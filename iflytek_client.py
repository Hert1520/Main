import base64
import hashlib
import hmac
import json
import random
import string
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.parse import quote

import requests

BASE_URL = "https://office-api-ist-dx.iflyaisol.com"


class IflytekApiError(RuntimeError):
    """Raised when the iFlytek API returns an error."""


@dataclass
class IflytekCredentials:
    app_id: str
    access_key_id: str
    access_key_secret: str


class IflytekTranscriber:
    def __init__(self, credentials: IflytekCredentials, base_url: str = BASE_URL, timeout: int = 30):
        self.credentials = credentials
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    @staticmethod
    def _random_string(length: int = 16) -> str:
        pool = string.ascii_letters + string.digits
        return "".join(random.choice(pool) for _ in range(length))

    @staticmethod
    def _date_time() -> str:
        return datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%dT%H:%M:%S%z")

    def _sign(self, params: Dict[str, Any]) -> str:
        to_sign = {k: v for k, v in params.items() if k != "signature" and v not in (None, "")}
        sorted_items = sorted(to_sign.items(), key=lambda x: x[0])
        base_string = "&".join(f"{quote(str(k), safe='')}={quote(str(v), safe='')}" for k, v in sorted_items)
        digest = hmac.new(
            self.credentials.access_key_secret.encode("utf-8"),
            base_string.encode("utf-8"),
            hashlib.sha1,
        ).digest()
        return base64.b64encode(digest).decode("utf-8")

    @staticmethod
    def _encode_params(params: Dict[str, Any]) -> Dict[str, str]:
        encoded: Dict[str, str] = {}
        for k, v in params.items():
            if v is None:
                continue
            encoded[k] = str(v)
        return encoded

    def upload(self, audio_path: str, language: str = "autodialect", **extra_params: Any) -> Dict[str, Any]:
        p = Path(audio_path)
        if not p.exists() or not p.is_file():
            raise FileNotFoundError(f"音频文件不存在: {audio_path}")

        common = {
            "appId": self.credentials.app_id,
            "accessKeyId": self.credentials.access_key_id,
            "dateTime": self._date_time(),
            "signatureRandom": self._random_string(),
            "fileSize": p.stat().st_size,
            "fileName": p.name,
            "language": language,
            **extra_params,
        }

        signature = self._sign(common)
        url = f"{self.base_url}/v2/upload"
        with p.open("rb") as f:
            response = requests.post(
                url,
                params=self._encode_params(common),
                headers={
                    "Content-Type": "application/octet-stream",
                    "signature": signature,
                },
                data=f,
                timeout=self.timeout,
            )

        data = response.json()
        if str(data.get("code")) != "000000":
            raise IflytekApiError(f"上传失败: {data}")
        return {
            "meta": common,
            "signature": signature,
            "response": data,
        }

    def get_result(self, order_id: str, signature_random: str, result_type: str = "transfer") -> Dict[str, Any]:
        params = {
            "accessKeyId": self.credentials.access_key_id,
            "dateTime": self._date_time(),
            "signatureRandom": signature_random,
            "orderId": order_id,
            "resultType": result_type,
        }
        signature = self._sign(params)
        response = requests.post(
            f"{self.base_url}/v2/getResult",
            params=self._encode_params(params),
            headers={
                "Content-Type": "application/json",
                "signature": signature,
            },
            data=json.dumps({}),
            timeout=self.timeout,
        )
        data = response.json()
        if str(data.get("code")) != "000000":
            raise IflytekApiError(f"查询失败: {data}")
        return data

    def transcribe(
        self,
        audio_path: str,
        language: str = "autodialect",
        poll_interval_sec: int = 5,
        max_wait_sec: int = 1800,
        **extra_params: Any,
    ) -> Dict[str, Any]:
        upload_data = self.upload(audio_path=audio_path, language=language, **extra_params)
        order_id = upload_data["response"]["content"]["orderId"]
        signature_random = upload_data["meta"]["signatureRandom"]

        started = time.time()
        last_result: Optional[Dict[str, Any]] = None

        while time.time() - started < max_wait_sec:
            result = self.get_result(order_id=order_id, signature_random=signature_random)
            last_result = result
            status = result.get("content", {}).get("orderInfo", {}).get("status")
            if status == 4:
                return {
                    "orderId": order_id,
                    "status": status,
                    "upload": upload_data["response"],
                    "result": result,
                }
            if status == -1:
                fail_type = result.get("content", {}).get("orderInfo", {}).get("failType")
                raise IflytekApiError(f"转写失败，failType={fail_type}, orderId={order_id}")
            time.sleep(poll_interval_sec)

        raise TimeoutError(f"转写超时，orderId={order_id}, 最后结果={last_result}")

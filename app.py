import os
import tempfile
from pathlib import Path

from flask import Flask, flash, redirect, render_template, request

from iflytek_client import IflytekCredentials, IflytekTranscriber

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev-secret")


@app.route("/", methods=["GET", "POST"])
def index():
    result_text = None
    raw_result = None

    if request.method == "POST":
        app_id = request.form.get("app_id", "").strip()
        access_key_id = request.form.get("access_key_id", "").strip()
        access_key_secret = request.form.get("access_key_secret", "").strip()
        language = request.form.get("language", "autodialect")
        poll_interval = int(request.form.get("poll_interval", "5"))
        max_wait = int(request.form.get("max_wait", "1800"))
        audio_file = request.files.get("audio_file")

        if not (app_id and access_key_id and access_key_secret and audio_file):
            flash("请填写完整凭证并上传音频文件。", "error")
            return redirect("/")

        suffix = Path(audio_file.filename or "audio.wav").suffix or ".wav"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            audio_file.save(tmp.name)
            temp_path = tmp.name

        try:
            client = IflytekTranscriber(
                credentials=IflytekCredentials(
                    app_id=app_id,
                    access_key_id=access_key_id,
                    access_key_secret=access_key_secret,
                )
            )
            output = client.transcribe(
                audio_path=temp_path,
                language=language,
                poll_interval_sec=poll_interval,
                max_wait_sec=max_wait,
            )
            raw_result = output
            order_result = output["result"].get("content", {}).get("orderResult", "")
            result_text = order_result
        except Exception as exc:  # noqa: BLE001
            flash(f"转写失败：{exc}", "error")
        finally:
            os.unlink(temp_path)

    return render_template("index.html", result_text=result_text, raw_result=raw_result)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)

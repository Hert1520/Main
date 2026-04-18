# 讯飞录音文件转写应用（Python Flask）

这是一个基于你提供文档实现的最小可用应用，封装了：

1. `POST /v2/upload`（上传音频，获取 `orderId`）
2. `POST /v2/getResult`（轮询结果，直到完成）

## 功能

- 支持上传本地音频文件
- 自动生成签名（HMAC-SHA1 + Base64）
- 自动轮询任务状态
- 页面显示 `orderResult` 与完整响应 JSON

## 快速开始

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

浏览器访问：`http://127.0.0.1:8000`

## 参数说明

- `language`：`autodialect` / `autominor`
- 轮询间隔：默认 5 秒
- 最大等待：默认 1800 秒（30 分钟）

## 注意事项

- 需要有效的 `AppID / AccessKeyId / AccessKeySecret`
- 请求时间格式采用 `yyyy-MM-dd'T'HH:mm:ss±HHmm`
- 上传格式、大小与时长必须满足文档限制（最大 5 小时 / 500MB）

## 目录

- `app.py`: Flask Web 应用
- `iflytek_client.py`: 签名、上传、查询与轮询逻辑
- `templates/index.html`: 页面模板

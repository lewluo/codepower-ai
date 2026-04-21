import binascii
import hashlib
import hmac
import json
import time
import uuid

import requests
import websocket

from config.logger import setup_logging
from core.providers.llm.base import LLMProviderBase
from core.utils.util import check_model_key

TAG = __name__
logger = setup_logging()


class LLMProvider(LLMProviderBase):
    def __init__(self, config):
        self.access_key = config.get("access_key", "")
        self.secret_key = config.get("secret_key", "")
        self.vendor_id = str(config.get("vendor_id", "") or "")
        self.app_id = str(config.get("app_id", "") or "")
        self.bot_id = str(config.get("bot_id", "") or "")
        self.device_id = config.get("device_id", "codepower-local-xiaozhi")
        self.device_name = config.get("device_name", "CodePower-Local-Xiaozhi")
        self.device_model = config.get("device_model", "codepower-xiaozhi-bridge")
        self.uid = config.get("uid", "codepower-local-user")
        self.auth_url = config.get("auth_url", "https://api.joyinside.com/auth/getToken")
        self.register_url = config.get(
            "register_url", "https://api.joyinside.com/device/register"
        )
        self.ws_url = config.get(
            "ws_url", "wss://ws.joyinside.com/soulmate/voiceChat/v1"
        )
        self.timeout = float(config.get("timeout", 20))
        self.max_wait_seconds = float(config.get("max_wait_seconds", 60))
        self.access_token = ""
        self.token_expires_at = 0.0
        self.session = requests.Session()
        self.session.trust_env = False

        for label, value in {
            "JoyInside access_key": self.access_key,
            "JoyInside secret_key": self.secret_key,
            "JoyInside vendor_id": self.vendor_id,
            "JoyInside app_id": self.app_id,
        }.items():
            if not value:
                logger.bind(tag=TAG).error(f"{label} 未配置")

        model_key_msg = check_model_key("JoyInside", self.access_key)
        if model_key_msg:
            logger.bind(tag=TAG).error(model_key_msg)

    def _sign(self, params):
        lower_params = {k.lower(): str(v) for k, v in params.items()}
        joint_params = "&".join(
            f"{k}={v}" for k, v in sorted(lower_params.items(), key=lambda item: item[0])
        )
        digest = hmac.new(
            self.secret_key.encode("utf-8"),
            joint_params.encode("utf-8"),
            digestmod=hashlib.md5,
        ).digest()
        return binascii.hexlify(digest).decode("utf-8")

    def _auth_payload(self):
        params = {
            "accessKeyId": self.access_key,
            "accessTimestamp": str(int(time.time() * 1000)),
            "accessNonce": str(uuid.uuid4()),
            "accessVersion": "V2",
        }
        params["accessSign"] = self._sign(params)
        return params

    def _get_token(self, bot_id=None):
        now = time.time()
        if self.access_token and now < self.token_expires_at - 60:
            return self.access_token

        params = self._auth_payload()
        if bot_id:
            params["botId"] = bot_id
        else:
            params["vendorId"] = self.vendor_id

        response = self.session.post(self.auth_url, json=params, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()
        access_token = data.get("accessToken")
        if not access_token:
            raise RuntimeError(
                f"JoyInside 获取 token 失败: code={data.get('code')} msg={data.get('msg')}"
            )

        self.access_token = access_token
        self.token_expires_at = now + int(data.get("expireIn", 7200))
        return access_token

    def _register_device(self):
        access_token = self._get_token()
        payload = {
            "vendorId": self.vendor_id,
            "appId": self.app_id,
            "type": "APP_ROBOT",
            "name": self.device_name,
            "deviceId": self.device_id,
            "deviceModel": self.device_model,
            "desc": "Local Xiaozhi to JoyInside bridge",
        }
        response = self.session.post(
            self.register_url,
            headers={"Authorization": f"Bearer {access_token}"},
            json=payload,
            timeout=self.timeout,
        )
        response.raise_for_status()
        data = response.json()
        bot_id = data.get("data")
        if not bot_id:
            raise RuntimeError(
                f"JoyInside 注册设备失败: state={data.get('state')} code={data.get('code')} result={data.get('result')}"
            )
        self.bot_id = bot_id
        self.access_token = ""
        self.token_expires_at = 0.0
        logger.bind(tag=TAG).info("JoyInside 测试设备注册成功")
        return bot_id

    def _ensure_bot_id(self):
        if self.bot_id:
            return self.bot_id
        return self._register_device()

    @staticmethod
    def _last_user_text(dialogue):
        for message in reversed(dialogue):
            if message.get("role") == "user" and message.get("content"):
                return message["content"]
        return ""

    def response(self, session_id, dialogue, **kwargs):
        query = self._last_user_text(dialogue)
        if not query:
            return

        try:
            bot_id = self._ensure_bot_id()
            access_token = self._get_token(bot_id=bot_id)
            request_id = str(uuid.uuid4())
            ws_session_id = f"{bot_id}_{session_id or uuid.uuid4().hex}"
            url = (
                f"{self.ws_url}?botId={bot_id}"
                f"&sessionId={ws_session_id}&requestId={request_id}"
            )

            ws = websocket.create_connection(
                url,
                header=[f"Authorization: Bearer {access_token}"],
                timeout=self.timeout,
            )
            try:
                ws.send(
                    json.dumps(
                        {
                            "mid": str(uuid.uuid4()),
                            "contentType": "TEXT",
                            "uid": self.uid,
                            "content": {"input": query},
                        },
                        ensure_ascii=False,
                    )
                )

                start = time.time()
                got_text = False
                while time.time() - start < self.max_wait_seconds:
                    raw = ws.recv()
                    if isinstance(raw, bytes):
                        continue

                    message = json.loads(raw)
                    content_type = message.get("contentType")
                    content = message.get("content") or {}

                    if content_type in {"AGENT", "ACTIVITY"}:
                        text = content.get("content") or ""
                        if text:
                            got_text = True
                            yield text
                        if content.get("finishReason") == "stop":
                            break

                    if content_type == "EVENT":
                        event_type = content.get("eventType")
                        if event_type in {"COMPLETE", "EMPTY_CONTENT"}:
                            break

                    if message.get("code") not in (None, 200):
                        raise RuntimeError(
                            f"JoyInside 下行错误: code={message.get('code')} msg={message.get('msg')}"
                        )

                if not got_text:
                    logger.bind(tag=TAG).warning("JoyInside 本轮没有返回文本")
            finally:
                ws.close()

        except Exception as e:
            logger.bind(tag=TAG).error(f"JoyInside 对话失败: {type(e).__name__}: {e}")
            yield "JoyInside 暂时没有接通。"

    def response_with_functions(self, session_id, dialogue, functions=None, **kwargs):
        for token in self.response(session_id, dialogue, **kwargs):
            yield token, None


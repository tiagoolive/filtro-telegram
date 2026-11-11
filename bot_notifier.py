import json
import urllib.request
import urllib.error
import asyncio
import html
from typing import Optional, Dict, Any


class BotNotifier:
    """
    Envia notificações push sonoras através de um bot oficial do Telegram (@BotFather).
    Como as mensagens vêm de outro remetente (o bot), o Telegram dispara alertas sonoros
    e pop-ups no celular e no desktop do usuário.
    """
    def __init__(self, token: Optional[str] = None):
        self.token = token.strip() if token else ""
        self.bot_info: Optional[Dict[str, Any]] = None

    @property
    def is_enabled(self) -> bool:
        return bool(self.token)

    def set_token(self, token: str):
        self.token = token.strip() if token else ""
        self.bot_info = None

    def _sync_request(self, endpoint: str, payload: Optional[dict] = None, suppress_error: bool = False) -> Optional[dict]:
        if not self.is_enabled:
            return None
        url = f"https://api.telegram.org/bot{self.token}/{endpoint}"
        try:
            if payload is not None:
                body = json.dumps(payload).encode("utf-8")
                req = urllib.request.Request(
                    url,
                    data=body,
                    headers={"Content-Type": "application/json"}
                )
            else:
                req = urllib.request.Request(url)

            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                if data.get("ok"):
                    return data.get("result")
        except urllib.error.HTTPError as e:
            if not suppress_error:
                try:
                    err_body = e.read().decode("utf-8")
                    err_json = json.loads(err_body)
                    print(f"[BOT NOTIFICADOR] Erro da API ({e.code}): {err_json.get('description')}")
                except Exception:
                    print(f"[BOT NOTIFICADOR] Erro HTTP ({e.code}) ao conectar ao bot.")
        except Exception as e:
            if not suppress_error:
                print(f"[BOT NOTIFICADOR] Falha de conexao: {e}")
        return None

    async def verify(self) -> Optional[Dict[str, Any]]:
        """Verifica se o token e valido e busca informacoes do bot."""
        if not self.is_enabled:
            return None
        self.bot_info = await asyncio.to_thread(self._sync_request, "getMe")
        return self.bot_info

    async def send_notification(
        self,
        chat_id: Any,
        matched_term: str,
        channel_title: str,
        reply_to_message_id: Optional[int] = None,
        extra_text: Optional[str] = None
    ) -> bool:
        """Envia mensagem de alerta com som e notificacao push ativados."""
        if not self.is_enabled:
            return False

        safe_term = html.escape(matched_term)
        safe_channel = html.escape(channel_title)

        text = (
            f"🎯 <b>Promoção Encontrada!</b>\n"
            f"🏷️ <b>Termo correspondente:</b> <code>{safe_term}</code>\n"
            f"📢 <b>Canal de origem:</b> {safe_channel}"
        )
        if extra_text:
            text += f"\n\n{html.escape(extra_text[:1500])}"

        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_notification": False  # Garante envio com som ativo!
        }
        if reply_to_message_id:
            payload["reply_to_message_id"] = reply_to_message_id

        res = await asyncio.to_thread(self._sync_request, "sendMessage", payload, bool(reply_to_message_id))
        # Se falhar com reply_to_message_id (ex: bot sem admin/privacidade ativa no grupo), tenta enviar sem reply
        if not res and reply_to_message_id:
            payload.pop("reply_to_message_id", None)
            res = await asyncio.to_thread(self._sync_request, "sendMessage", payload, False)

        return bool(res)


import json
import os
from typing import Dict, Any, List

DEFAULT_CONFIG: Dict[str, Any] = {
    "monitor_all_channels": True,
    "channels": [],
    "keywords": [
        "rtx 4060",
        "rtx 4070",
        "ps5",
        "playstation 5",
        "nintendo switch",
        "kindle",
        "air fryer",
        "iphone"
    ],
    "negative_keywords": [
        "capa",
        "capinha",
        "pelicula",
        "suporte",
        "recondicionado",
        "usado"
    ],
    "target_chat": "me",
    "bot_token": "",
    "add_tag_reply": True,
    "cooldown_minutes": 15
}


class ConfigManager:
    def __init__(self, file_path: str = "config.json"):
        self.file_path = file_path
        self._last_mtime: float = 0.0
        self.config = self._load()

    def _load(self, fallback_existing: bool = False) -> Dict[str, Any]:
        if not os.path.exists(self.file_path):
            self._save_data(DEFAULT_CONFIG)
            return DEFAULT_CONFIG.copy()

        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                # Garante que chaves faltantes sejam preenchidas com padrão
                for k, v in DEFAULT_CONFIG.items():
                    if k not in data:
                        data[k] = v
                self._last_mtime = os.path.getmtime(self.file_path)
                return data
        except Exception as e:
            print(f"[AVISO] Erro ao ler {self.file_path}: {e}.")
            if fallback_existing and hasattr(self, "config"):
                return self.config
            return DEFAULT_CONFIG.copy()

    def reload_if_changed(self) -> bool:
        """Recarrega o config.json automaticamente caso o arquivo tenha sido alterado no disco."""
        if not os.path.exists(self.file_path):
            return False
        try:
            mtime = os.path.getmtime(self.file_path)
            if mtime != self._last_mtime:
                new_config = self._load(fallback_existing=True)
                self.config = new_config
                self._last_mtime = mtime
                return True
        except OSError:
            pass
        return False

    def _save_data(self, data: Dict[str, Any]):
        try:
            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            self._last_mtime = os.path.getmtime(self.file_path)
        except Exception as e:
            print(f"[ERRO] Falha ao salvar {self.file_path}: {e}")

    def save(self):
        self._save_data(self.config)

    # --- Palavras-chave ---
    def add_keyword(self, word: str) -> bool:
        clean = word.strip().lower()
        current = [k.lower() for k in self.config.get("keywords", [])]
        if clean and clean not in current:
            self.config.setdefault("keywords", []).append(word.strip())
            self.save()
            return True
        return False

    def remove_keyword(self, word: str) -> bool:
        clean = word.strip().lower()
        keywords = self.config.get("keywords", [])
        new_keywords = [k for k in keywords if k.strip().lower() != clean]
        if len(new_keywords) != len(keywords):
            self.config["keywords"] = new_keywords
            self.save()
            return True
        return False

    # --- Palavras bloqueadas (Negativas) ---
    def add_negative_keyword(self, word: str) -> bool:
        clean = word.strip().lower()
        current = [k.lower() for k in self.config.get("negative_keywords", [])]
        if clean and clean not in current:
            self.config.setdefault("negative_keywords", []).append(word.strip())
            self.save()
            return True
        return False

    def remove_negative_keyword(self, word: str) -> bool:
        clean = word.strip().lower()
        negs = self.config.get("negative_keywords", [])
        new_negs = [k for k in negs if k.strip().lower() != clean]
        if len(new_negs) != len(negs):
            self.config["negative_keywords"] = new_negs
            self.save()
            return True
        return False

    # --- Canais ---
    def add_channel(self, channel_ref: str) -> bool:
        clean = channel_ref.strip()
        channels = self.config.setdefault("channels", [])
        if clean not in channels:
            channels.append(clean)
            self.save()
            return True
        return False

    def remove_channel(self, channel_ref: str) -> bool:
        clean = channel_ref.strip()
        channels = self.config.get("channels", [])
        if clean in channels:
            channels.remove(clean)
            self.save()
            return True
        return False

    def set_monitor_all(self, val: bool):
        self.config["monitor_all_channels"] = bool(val)
        self.save()

    def set_target_chat(self, target: str):
        self.config["target_chat"] = target.strip()
        self.save()

    def set_bot_token(self, token: str):
        self.config["bot_token"] = token.strip()
        self.save()

    @property
    def bot_token(self) -> str:
        return self.config.get("bot_token", "")

    @property
    def keywords(self) -> List[str]:
        return self.config.get("keywords", [])

    @property
    def negative_keywords(self) -> List[str]:
        return self.config.get("negative_keywords", [])

    @property
    def monitor_all(self) -> bool:
        return self.config.get("monitor_all_channels", True)

    @property
    def channels(self) -> List[Any]:
        return self.config.get("channels", [])

    @property
    def target_chat(self) -> str:
        return self.config.get("target_chat", "me")

    @property
    def add_tag_reply(self) -> bool:
        return self.config.get("add_tag_reply", True)

    @property
    def cooldown_minutes(self) -> int:
        return self.config.get("cooldown_minutes", 15)


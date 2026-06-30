import itertools
from backend.config import settings

class ApiKeyManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ApiKeyManager, cls).__new__(cls)
            
            keys_str = settings.openrouter_api_keys
            keys = [k.strip() for k in keys_str.split(",") if k.strip()]
            
            if settings.openrouter_api_key and settings.openrouter_api_key not in keys:
                keys.append(settings.openrouter_api_key)
            
            # If no keys are provided, we should probably throw an error,
            # but for safety we'll use an empty cycle or fallback
            if not keys:
                keys = [""]
                
            cls._instance.keys = keys
            cls._instance._cycle = itertools.cycle(keys)
        return cls._instance

    def get_next_key(self) -> str:
        return next(self._cycle)

api_key_manager = ApiKeyManager()

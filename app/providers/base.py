from abc import ABC, abstractmethod
from typing import Dict, Any

class ProviderError(Exception):
    pass

class BaseProvider(ABC):
    name: str

    @abstractmethod
    async def ask(self, query: str, intent: str, meta: Dict[str, Any]) -> str:
        ...

from typing import Any, Dict, List
from abc import ABC, abstractmethod
from langchain_core.language_models import BaseChatModel


class BaseLLM(ABC):
    """Abstract base class for LLM implementations"""

    def __init__(self, temperature: float = 0.0, **kwargs):
        self.temperature = temperature
        self.llm = self._initialize_llm(**kwargs)

    @abstractmethod
    def _initialize_llm(self, **kwargs) -> BaseChatModel:
        """Initialize the specific LLM implementation"""
        pass

    def invoke(self, messages: Any, config: dict = None, **kwargs) -> Any:
        """Invoke the LLM with messages"""
        try:
            if config:
                result = self.llm.invoke(messages, config=config, **kwargs)
            else:
                result = self.llm.invoke(messages, **kwargs)
        except TypeError as e:
            result = self.llm.invoke(messages)

        return result

    def generate_response(self, prompt: str, **kwargs) -> str:
        pass

    @abstractmethod
    def generate_chat_response(self, messages: List[Dict[str, str]], **kwargs) -> str:
        pass

    @abstractmethod
    def stream_response(self, prompt: str, **kwargs):
        pass

    @abstractmethod
    async def agenerate_response(self, prompt: str, **kwargs) -> str:
        pass

    # def stream(self, messages: Any, **kwargs) -> Any:
    #     """Stream responses from the LLM"""
    #     if isinstance(messages, str):
    #         messages = [HumanMessage(content=messages)]
    #     elif isinstance(messages, tuple):
    #         if len(messages) == 1 and isinstance(messages[0], str):
    #             messages = [HumanMessage(content=messages[0])]
    #         else:
    #             raise ValueError(f"Invalid tuple input: {messages}")
    #     elif not isinstance(messages, list):
    #         raise ValueError(f"Expected str or list of messages, got {type(messages)}")

    #     result = self.llm.stream(messages, **kwargs)
    #     return result

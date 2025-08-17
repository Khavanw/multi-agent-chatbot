import logging
import os
from pathlib import Path
import sys
from typing import List, Dict, Any, Optional, Sequence, AsyncGenerator
from dotenv import load_dotenv
import google.generativeai as genai
import asyncio

# ✅ THÊM IMPORT CHO LLAMAINDEX COMPATIBILITY
from llama_index.core.llms import LLM as LlamaIndexLLM
from llama_index.core.llms import CompletionResponse, CompletionResponseGen
from llama_index.core.llms import ChatMessage, ChatResponse, ChatResponseGen
from llama_index.core.base.llms.types import MessageRole
from llama_index.core.bridge.pydantic import Field

from app.settings import APP_SETTINGS
from .base_llm import BaseLLM

logger = logging.getLogger(__name__)


class GeminiLLM(BaseLLM):
    def __init__(self, api_key: str, model_name: str = "gemini-1.5-flash"):
        if not api_key:
            raise ValueError("Gemini API key is required.")

        self.api_key = api_key
        self.model_name = model_name

        logger.info("🔑 Configuring Google Generative AI with Gemini API key...")
        genai.configure(api_key=api_key)

        try:
            self.model = genai.GenerativeModel(model_name)
            logger.info(f"✅ Successfully initialized Gemini LLM: {model_name}")
        except Exception as e:
            logger.error(f"❌ Failed to initialize Gemini LLM: {e}")
            raise

        # Gọi constructor của parent class
        super().__init__(temperature=0.7)

    def _initialize_llm(self, **kwargs):
        """Initialize the LLM - Required by BaseLLM interface"""
        return None

    def get_llamaindex_llm(self):
        """Trả về LlamaIndex compatible LLM wrapper"""
        return LlamaIndexGeminiWrapper(self)

    def generate_response(self, prompt: str, **kwargs) -> str:
        try:
            logger.debug(f"🤖 Generating response for prompt: {prompt[:100]}...")
            generation_config = {
                "temperature": kwargs.get("temperature", 0.7),
                "top_p": kwargs.get("top_p", 0.8),
                "top_k": kwargs.get("top_k", 40),
                "max_output_tokens": kwargs.get("max_output_tokens", 2048),
            }

            response = self.model.generate_content(
                prompt, generation_config=generation_config
            )
            return response.text

        except Exception as e:
            logger.error(f"❌ Failed to generate response: {e}")
            raise

    def generate_chat_response(self, messages: List[Dict[str, str]], **kwargs) -> str:
        try:
            chat_history = []
            current_prompt = ""

            for message in messages:
                if message["role"] == "user":
                    current_prompt = message["content"]
                elif message["role"] == "assistant":
                    chat_history.append(
                        {"parts": [{"text": current_prompt}], "role": "user"}
                    )
                    chat_history.append(
                        {"parts": [{"text": message["content"]}], "role": "model"}
                    )

            if messages[-1]["role"] == "user":
                current_prompt = messages[-1]["content"]

            chat = self.model.start_chat(history=chat_history)
            response = chat.send_message(current_prompt)
            return response.text

        except Exception as e:
            logger.error(f"❌ Failed to generate chat response: {e}")
            raise

    def stream_response(self, prompt: str, **kwargs):
        try:
            logger.debug(f"🔄 Streaming response for prompt: {prompt[:100]}...")
            generation_config = {
                "temperature": kwargs.get("temperature", 0.7),
                "top_p": kwargs.get("top_p", 0.8),
                "top_k": kwargs.get("top_k", 40),
                "max_output_tokens": kwargs.get("max_output_tokens", 2048),
            }

            response = self.model.generate_content(
                prompt, generation_config=generation_config, stream=True
            )

            for chunk in response:
                if chunk.text:
                    yield chunk.text

        except Exception as e:
            logger.error(f"❌ Failed to stream response: {e}")
            raise

    async def agenerate_response(self, prompt: str, **kwargs) -> str:
        return await asyncio.to_thread(self.generate_response, prompt, **kwargs)


# ✅ FIXED LLAMAINDEX WRAPPER CLASS - COMPLETE IMPLEMENTATION
class LlamaIndexGeminiWrapper(LlamaIndexLLM):
    """
    FIXED: Wrapper đầy đủ để làm cho GeminiLLM tương thích với LlamaIndex
    Implements tất cả required abstract methods
    """

    # ✅ Khai báo fields cho Pydantic
    gemini_llm: Any = Field(description="GeminiLLM instance")
    model_name: str = Field(default="gemini-1.5-flash", description="Model name")
    temperature: float = Field(default=0.7, description="Temperature for generation")
    max_tokens: int = Field(default=2048, description="Maximum tokens to generate")

    def __init__(self, gemini_llm: GeminiLLM, **kwargs):
        super().__init__(
            gemini_llm=gemini_llm,
            model_name=gemini_llm.model_name,
            temperature=0.7,
            max_tokens=2048,
            **kwargs,
        )

    @property
    def metadata(self) -> Dict[str, Any]:
        """Get LLM metadata"""
        return {
            "model_name": self.model_name,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "llm_type": "gemini",
        }

    # ================== SYNC METHODS ==================

    def complete(self, prompt: str, **kwargs) -> CompletionResponse:
        """Complete a prompt - sync version"""
        try:
            logger.debug(f"🔄 LlamaIndex sync complete: {prompt[:50]}...")

            temperature = kwargs.get("temperature", self.temperature)
            max_tokens = kwargs.get("max_tokens", self.max_tokens)

            response_text = self.gemini_llm.generate_response(
                prompt, temperature=temperature, max_output_tokens=max_tokens, **kwargs
            )

            return CompletionResponse(text=response_text, additional_kwargs=kwargs)

        except Exception as e:
            logger.error(f"❌ Error in complete: {e}")
            return CompletionResponse(text=f"Error: {str(e)}", additional_kwargs=kwargs)

    def stream_complete(self, prompt: str, **kwargs) -> CompletionResponseGen:
        """Stream complete a prompt - sync version"""
        try:
            logger.debug(f"🔄 LlamaIndex sync stream_complete: {prompt[:50]}...")

            temperature = kwargs.get("temperature", self.temperature)
            max_tokens = kwargs.get("max_tokens", self.max_tokens)

            for chunk in self.gemini_llm.stream_response(
                prompt, temperature=temperature, max_output_tokens=max_tokens, **kwargs
            ):
                yield CompletionResponse(
                    text=chunk, delta=chunk, additional_kwargs=kwargs
                )

        except Exception as e:
            logger.error(f"❌ Error in stream_complete: {e}")
            yield CompletionResponse(text=f"Error: {str(e)}", additional_kwargs=kwargs)

    def chat(self, messages: Sequence[ChatMessage], **kwargs) -> ChatResponse:
        """Chat completion - sync version"""
        try:
            logger.debug(f"🔄 LlamaIndex sync chat with {len(messages)} messages")

            # Convert LlamaIndex ChatMessages to GeminiLLM format
            formatted_messages = self._convert_messages(messages)

            response_text = self.gemini_llm.generate_chat_response(
                formatted_messages, **kwargs
            )

            response_message = ChatMessage(
                role=MessageRole.ASSISTANT, content=response_text
            )

            return ChatResponse(message=response_message, additional_kwargs=kwargs)

        except Exception as e:
            logger.error(f"❌ Error in chat: {e}")
            error_message = ChatMessage(
                role=MessageRole.ASSISTANT, content=f"Error: {str(e)}"
            )
            return ChatResponse(message=error_message, additional_kwargs=kwargs)

    def stream_chat(self, messages: Sequence[ChatMessage], **kwargs) -> ChatResponseGen:
        """Stream chat completion - sync version"""
        try:
            logger.debug(
                f"🔄 LlamaIndex sync stream_chat with {len(messages)} messages"
            )

            # Convert to prompt for streaming
            prompt = self._messages_to_prompt(messages)

            accumulated_text = ""
            for chunk in self.gemini_llm.stream_response(prompt, **kwargs):
                accumulated_text += chunk

                response_message = ChatMessage(
                    role=MessageRole.ASSISTANT, content=accumulated_text
                )

                yield ChatResponse(
                    message=response_message, delta=chunk, additional_kwargs=kwargs
                )

        except Exception as e:
            logger.error(f"❌ Error in stream_chat: {e}")
            error_message = ChatMessage(
                role=MessageRole.ASSISTANT, content=f"Error: {str(e)}"
            )
            yield ChatResponse(message=error_message, additional_kwargs=kwargs)

    # ================== ASYNC METHODS (MISSING IMPLEMENTATIONS) ==================

    async def acomplete(self, prompt: str, **kwargs) -> CompletionResponse:
        """✅ FIXED: Async complete - was missing implementation"""
        try:
            logger.debug(f"🔄 LlamaIndex async complete: {prompt[:50]}...")

            response_text = await self.gemini_llm.agenerate_response(prompt, **kwargs)

            return CompletionResponse(text=response_text, additional_kwargs=kwargs)

        except Exception as e:
            logger.error(f"❌ Error in acomplete: {e}")
            return CompletionResponse(text=f"Error: {str(e)}", additional_kwargs=kwargs)

    async def astream_complete(
        self, prompt: str, **kwargs
    ) -> AsyncGenerator[CompletionResponse, None]:
        """✅ FIXED: Async stream complete - THIS WAS MISSING!"""
        try:
            logger.debug(f"🔄 LlamaIndex async stream_complete: {prompt[:50]}...")

            # Since GeminiLLM doesn't have async streaming, we'll use thread pool
            def _sync_stream():
                return list(self.stream_complete(prompt, **kwargs))

            # Run in thread pool and yield results
            responses = await asyncio.to_thread(_sync_stream)
            for response in responses:
                yield response

        except Exception as e:
            logger.error(f"❌ Error in astream_complete: {e}")
            yield CompletionResponse(text=f"Error: {str(e)}", additional_kwargs=kwargs)

    async def achat(self, messages: Sequence[ChatMessage], **kwargs) -> ChatResponse:
        """✅ FIXED: Async chat - was incomplete"""
        try:
            logger.debug(f"🔄 LlamaIndex async chat with {len(messages)} messages")

            # Run sync chat in thread pool
            return await asyncio.to_thread(self.chat, messages, **kwargs)

        except Exception as e:
            logger.error(f"❌ Error in achat: {e}")
            error_message = ChatMessage(
                role=MessageRole.ASSISTANT, content=f"Error: {str(e)}"
            )
            return ChatResponse(message=error_message, additional_kwargs=kwargs)

    async def astream_chat(
        self, messages: Sequence[ChatMessage], **kwargs
    ) -> AsyncGenerator[ChatResponse, None]:
        """✅ FIXED: Async stream chat - THIS WAS MISSING!"""
        try:
            logger.debug(
                f"🔄 LlamaIndex async stream_chat with {len(messages)} messages"
            )

            # Run sync stream_chat in thread pool
            def _sync_stream_chat():
                return list(self.stream_chat(messages, **kwargs))

            responses = await asyncio.to_thread(_sync_stream_chat)
            for response in responses:
                yield response

        except Exception as e:
            logger.error(f"❌ Error in astream_chat: {e}")
            error_message = ChatMessage(
                role=MessageRole.ASSISTANT, content=f"Error: {str(e)}"
            )
            yield ChatResponse(message=error_message, additional_kwargs=kwargs)

    # ================== HELPER METHODS ==================

    def _convert_messages(
        self, messages: Sequence[ChatMessage]
    ) -> List[Dict[str, str]]:
        """Convert LlamaIndex ChatMessages to GeminiLLM format"""
        formatted_messages = []
        for message in messages:
            role = "user" if message.role == MessageRole.USER else "assistant"
            if message.role == MessageRole.SYSTEM:
                role = "user"  # Gemini doesn't have system role

            formatted_messages.append({"role": role, "content": message.content})

        return formatted_messages

    def _messages_to_prompt(self, messages: Sequence[ChatMessage]) -> str:
        """Convert messages to a single prompt for streaming"""
        prompt_parts = []
        for message in messages:
            if message.role == MessageRole.USER:
                role_prefix = "User: "
            elif message.role == MessageRole.ASSISTANT:
                role_prefix = "Assistant: "
            else:  # SYSTEM
                role_prefix = "System: "

            prompt_parts.append(f"{role_prefix}{message.content}")

        return "\n".join(prompt_parts)


# ✅ FACTORY FUNCTION
def create_gemini_llm(
    api_key: str = None, model_name: str = "gemini-1.5-flash"
) -> GeminiLLM:
    """Factory function để tạo GeminiLLM instance"""
    try:
        if not api_key:
            api_key = APP_SETTINGS.GEMINI_API_KEY

        if not api_key:
            raise ValueError("Gemini API key is required")

        logger.info(f"🚀 Creating GeminiLLM with model: {model_name}")
        return GeminiLLM(api_key=api_key, model_name=model_name)

    except Exception as e:
        logger.error(f"❌ Failed to create GeminiLLM: {e}")
        raise

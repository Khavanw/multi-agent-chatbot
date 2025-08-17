from typing import Union
from langchain_core.messages import BaseMessage


def convert_chunk_to_text(chunk: Union[dict, str]) -> str:
    try:
        if isinstance(chunk, dict):
            for node_name, node_update in chunk.items():
                messages = node_update.get("messages", [])
                if messages:
                    last_msg = messages[-1]
                    if isinstance(last_msg, BaseMessage):
                        return f"{node_name}: {last_msg.content}"
                    elif isinstance(last_msg, dict) and "content" in last_msg:
                        return f"{node_name}: {last_msg['content']}"
        return str(chunk)
    except Exception as e:
        return f"[ERROR] {e}"

from typing import Generator

from app.utils.chunk_parser import convert_chunk_to_text
from app.tools.rag_mem_agent import RetrieverMem
from app.tools.research_agent import ResearchAgent
from app.tools.web_search_agent import WebSearchAgent
from app.tools.rag_vectordb_agent import RetrieverVectordb
from app.supervisor import AgentSupervisor


class WebSearchService:
    @staticmethod
    def run(content: str) -> Generator[str, None, None]:
        research_agent = WebSearchAgent().web_search_agent()
        messages = [{"role": "user", "content": content}]

        for chunk in research_agent.stream({"messages": messages}):
            yield convert_chunk_to_text(chunk) + "\n"


class DeepResearchService:
    @staticmethod
    def run(content: str) -> Generator[str, None, None]:
        research_agent = ResearchAgent().research_agent()
        messages = [{"role": "user", "content": content}]

        for chunk in research_agent.stream({"messages": messages}):
            yield convert_chunk_to_text(chunk) + "\n"


class RetrieverVectordbService:
    @staticmethod
    def run(content: str) -> Generator[str, None, None]:
        research_agent = RetrieverVectordb().retriever_vectordb()
        messages = [{"role": "user", "content": content}]

        for chunk in research_agent.stream({"messages": messages}):
            yield convert_chunk_to_text(chunk) + "\n"


class RetrieverMemService:
    @staticmethod
    def run(content: str) -> Generator[str, None, None]:
        research_agent = RetrieverMem().retriever_mem()
        messages = [{"role": "user", "content": content}]

        for chunk in research_agent.stream({"messages": messages}):
            yield convert_chunk_to_text(chunk) + "\n"


class AgentSupervisorService:
    @staticmethod
    def run(content: str) -> Generator[str, None, None]:
        research_agent = AgentSupervisor().agent_supervisor()
        messages = [{"role": "user", "content": content}]

        for chunk in research_agent.stream({"messages": messages}):
            yield convert_chunk_to_text(chunk) + "\n"

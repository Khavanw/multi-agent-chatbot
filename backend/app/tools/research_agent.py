import os
from langchain_tavily import TavilySearch
from langgraph.prebuilt import create_react_agent

from app.settings import APP_SETTINGS
from app.llm_loader import AzureLLMFactory
from app.services.langfuse.client import LangfuseClient


class ResearchAgent:
    def __init__(self, max_results: int = 10):
        self._set_api_key(APP_SETTINGS.TAVILY_API_KEY)
        self.searcher = TavilySearch(max_results=max_results)
        self.llm = AzureLLMFactory().create()
        self.langfuse_client = LangfuseClient()

    def _set_api_key(self, key: str):
        os.environ["TAVILY_API_KEY"] = key

    def web_search(self, query: str) -> str:
        """Searches the web using Tavily and returns the top result."""
        results = self.searcher.invoke(query)
        return results["results"][0]["content"] if results.get("results") else ""

    def research_agent(self):
        research_agent = create_react_agent(
            model=self.llm,
            tools=[self.web_search],
            prompt=self.langfuse_client.get_prompt("research_agent"),
            name="research_agent",
        )
        return research_agent

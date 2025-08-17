import os
from langchain_core.tools import Tool
from langchain_google_community import GoogleSearchAPIWrapper
from langgraph.prebuilt import create_react_agent

from app.settings import APP_SETTINGS
from app.llm_loader import AzureLLMFactory
from app.services.langfuse.client import LangfuseClient


class WebSearchAgent:
    def __init__(self):
        self.searcher = GoogleSearchAPIWrapper(
            google_api_key=APP_SETTINGS.GOOGLE_API_KEY,
            google_cse_id=APP_SETTINGS.GOOGLE_CSE_ID,
        )
        self.llm = AzureLLMFactory().create()
        self.langfuse_client = LangfuseClient()
        self.google_tool = Tool(
            name="google_search",
            description="Search Google for recent results.",
            func=self.searcher.run,
        )

    def web_search(self, query: str) -> str:
        """Searches the web using Google API and returns the top result."""
        return self.google_tool.run(query)

    def web_search_agent(self):
        web_search_agent = create_react_agent(
            model=self.llm,
            tools=[self.web_search],
            prompt=self.langfuse_client.get_prompt("research_agent"),
            name="web_search_agent",
        )
        return web_search_agent

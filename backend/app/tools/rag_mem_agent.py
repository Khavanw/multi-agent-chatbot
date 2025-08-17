from typing import List
from app.retriever.mem import InMemoryRetriever
from langgraph.prebuilt import create_react_agent
from app.llm_loader import AzureLLMFactory


class RetrieverMem:
    def __init__(self):
        self.llm = AzureLLMFactory().create()
        self.retriever = InMemoryRetriever().vector_store()
        self._agent = None

    def retriever_data(self, query: str, top_k: int = 5) -> List[str]:
        """
        Search and return information from the vector store.

        Args:
            query (str): The search query.
            top_k (int): Number of top results to return. Defaults to 5.

        Returns:
            List[str]: List of document contents matching the query.

        Raises:
            ValueError: If query is empty or invalid.
        """
        if not query or not isinstance(query, str):
            raise ValueError("Query must be a non-empty string")
        return self.retriever.invoke(query, k=top_k)

    def retriever_mem(self):
        """
        Create and return a research agent for retrieval tasks.

        Returns:
            The configured react agent.
        """
        if not self._agent:
            self._agent = create_react_agent(
                model=self.llm,
                tools=[self.retriever_data],
                prompt=(
                    "You are a research agent.\n\n"
                    "INSTRUCTIONS:\n"
                    "- Assist with research-related tasks based on provided data.\n"
                    "- Respond ONLY with the results of your work."
                ),
                name="retriever_mem",
            )
        return self._agent

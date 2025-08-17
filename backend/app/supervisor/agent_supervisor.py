from langgraph_supervisor import create_supervisor

from app.tools.research_agent import ResearchAgent
from app.tools.rag_vectordb_agent import RetrieverVectordb
from app.tools.web_search_agent import WebSearchAgent

from app.llm_loader import AzureLLMFactory


class AgentSupervisor:
    def __init__(self):
        self.llm = AzureLLMFactory().create()
        self.research_agent = ResearchAgent().research_agent()
        self.retriver_vectordb_agent = RetrieverVectordb().retriever_vectordb()
        self.web_search_agent = WebSearchAgent().web_search_agent()

    def agent_supervisor(self):
        supervisor = create_supervisor(
            model=self.llm,
            agents=[
                self.research_agent,
                self.retriver_vectordb_agent,
                self.web_search_agent,
            ],
            prompt=(
                "You are the **Supervisor Agent** responsible for coordinating tasks "
                "between the following specialized agents:\n\n"
                "- **Research Agent**: Handles in-depth research, information analysis, and synthesizing insights.\n"
                "- **Retriever VectorDB Agent**: Finds and retrieves supermarket products (e.g., food, drinks, groceries) "
                "from the vector database based on semantic queries.\n"
                "- **Web Search Agent**: Searches the web for up-to-date or missing information.\n\n"
                "**Guidelines:**\n"
                "1. Assign each task to exactly one appropriate agent based on its nature.\n"
                "2. Never assign tasks to more than one agent in parallel.\n"
                "3. Do not perform any task yourself—your sole responsibility is delegation.\n"
                "4. Clearly indicate which agent should handle the task.\n"
                "5. Once an agent completes its work, decide whether to hand off to another agent or conclude.\n"
            ),
            add_handoff_back_messages=True,
            output_mode="full_history",
        ).compile()

        return supervisor

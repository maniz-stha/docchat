from langgraph.graph import StateGraph, END
from typing import TypedDict, List, Dict
from .research_agent import ResearchAgent
from .verification_agent import VerificationAgent
from langchain.schema import Document
from langchain.retrievers import EnsembleRetriever
import logging

logger = logging.getLogger(__name__)

class AgentState(TypedDict):
    question: str
    documents: List[Document]
    draft_answer: str
    verification_report: str
    retriever: EnsembleRetriever
    attempts: int

class AgentWorkflow:
    def __init__(self):
        self.researcher = ResearchAgent()
        self.verifier = VerificationAgent()
        self.compiled_workflow = self.build_workflow()  # Compile once during initialization
        
    def build_workflow(self):
        """Create and compile the multi-agent workflow."""
        workflow = StateGraph(AgentState)
        
        # Add nodes
        workflow.add_node("research", self._research_step)
        workflow.add_node("verify", self._verification_step)
        
        # Define edges
        workflow.set_entry_point("research")
        workflow.add_edge("research", "verify")
        workflow.add_conditional_edges(
            "verify",
            self._decide_next_step,
            {
                "re_research": "research",
                "end": END
            }
        )
        return workflow.compile()
    
    def full_pipeline(self, question: str, retriever: EnsembleRetriever):
        try:
            print(f"[DEBUG] Starting full_pipeline with question='{question}'")
            documents = retriever.invoke(question)
            logger.info(f"Retrieved {len(documents)} relevant documents (from .invoke)")

            initial_state = AgentState(
                question=question,
                documents=documents,
                draft_answer="",
                verification_report="",
                retriever=retriever,
                attempts=0,
            )
            
            final_state = self.compiled_workflow.invoke(initial_state)
            
            return {
                "draft_answer": final_state["draft_answer"],
                "verification_report": final_state["verification_report"]
            }
        except Exception as e:
            logger.error(f"Workflow execution failed: {e}")
            raise
    
    def _research_step(self, state: AgentState) -> Dict:
        print(f"[DEBUG] Entered _research_step with question='{state['question']}'")
        result = self.researcher.generate(state["question"], state["documents"])
        print("[DEBUG] Researcher returned draft answer.")
        return {"draft_answer": result["draft_answer"], "attempts": state["attempts"] + 1}
    
    def _verification_step(self, state: AgentState) -> Dict:
        print("[DEBUG] Entered _verification_step. Verifying the draft answer...")
        result = self.verifier.check(state["draft_answer"], state["documents"])
        print("[DEBUG] VerificationAgent returned a verification report.")
        return {"verification_report": result["verification_report"]}
    
    def _decide_next_step(self, state: AgentState) -> str:
        verification_report = state["verification_report"]
        print(f"[DEBUG] _decide_next_step with verification_report='{verification_report}'")
        # ponytail: one retry avoids an unbounded loop; add a better repair strategy if quality data justifies it.
        if state["attempts"] < 2 and ("Supported: NO" in verification_report or "Relevant: NO" in verification_report):
            logger.info("[DEBUG] Verification indicates re-research needed.")
            return "re_research"
        else:
            logger.info("[DEBUG] Verification successful, ending workflow.")
            return "end"

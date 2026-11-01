# graph.py
from typing import TypedDict
from langgraph.graph import StateGraph, END
from llm_client import LLMClient
from rule_engine import RuleEngine
from agents.diagnosis import DiagnosisAgent
from agents.decision import DecisionAgent
from agents.explain import ExplainAgent


class AgentState(TypedDict):
    event: dict
    diagnosis: dict | None
    decision: dict | None
    explanation: str
    error: str


class IndustrialAgentGraph:
    def __init__(self):
        self.llm = LLMClient()
        self.rule_engine = RuleEngine()
        self.diagnosis_agent = DiagnosisAgent(self.llm, self.rule_engine)
        self.decision_agent = DecisionAgent(self.llm)
        self.explain_agent = ExplainAgent(self.llm)
        self.graph = self._build()

    def _build(self):
        g = StateGraph(AgentState)
        g.add_node("diagnosis", self._diagnosis_node)
        g.add_node("decision", self._decision_node)
        g.add_node("explain", self._explain_node)
        g.set_entry_point("diagnosis")
        g.add_conditional_edges(
            "diagnosis",
            self._route_after_diagnosis,
            {"decision": "decision", END: END}
        )
        g.add_edge("decision", "explain")
        g.add_edge("explain", END)
        return g.compile()

    async def _diagnosis_node(self, state):
        try:
            return {"diagnosis": await self.diagnosis_agent.run(state["event"])}
        except Exception as e:
            return {"error": f"诊断失败: {e}", "diagnosis": None}

    async def _decision_node(self, state):
        try:
            return {"decision": await self.decision_agent.run(state["diagnosis"])}
        except Exception as e:
            return {"error": f"决策失败: {e}", "decision": None}

    async def _explain_node(self, state):
        try:
            return {"explanation": await self.explain_agent.run(state["decision"])}
        except Exception as e:
            return {"explanation": f"解释失败: {e}"}

    def _route_after_diagnosis(self, state):
        if state.get("error"):
            return END
        diag = state.get("diagnosis")
        if not diag:
            return END
        if diag.get("llm_conclusion") == "正常" and diag.get("rule_conclusion") == "正常":
            return END
        return "decision"

    async def ainvoke(self, event: dict) -> dict:
        return await self.graph.ainvoke({
            "event": event,
            "diagnosis": None,
            "decision": None,
            "explanation": "",
            "error": ""
        })
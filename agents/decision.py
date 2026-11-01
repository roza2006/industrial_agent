# agents/decision.py
from llm_client import LLMClient
from tools import TOOLS_SCHEMA, execute_tool

DECISION_SYSTEM = """你是工业决策专家。你会收到诊断Agent的输出，
请决定是否告警、告警级别、以及建议动作。

决策规则：
1. 诊断结论"异常"且置信度"高" → critical告警
2. 诊断结论"疑似异常" → warning告警
3. LLM与规则引擎结论不一致 → 升级为人工审核
4. 连续多次同类异常 → 升级告警级别
5. 调用 send_alarm 工具发送告警

输出格式：
- 决策: 告警/不告警/升级人工
- 级别: info/warning/critical
- 理由: 简要说明
"""

class DecisionAgent:
    def __init__(self, llm: LLMClient):
        self.llm = llm
        self.alarm_history: list[dict] = []

    async def run(self, diagnosis: dict) -> dict:
        if not diagnosis["consistent"]:
            return {
                "decision": "升级人工",
                "level": "warning",
                "reason": f"LLM({diagnosis['llm_conclusion']})与规则({diagnosis['rule_conclusion']})不一致",
                "diagnosis": diagnosis,
                "requires_human": True
            }

        messages = [
            {"role": "system", "content": DECISION_SYSTEM},
            {"role": "user", "content": f"""诊断意见：
{diagnosis['llm_diagnosis']}

规则引擎结论：{diagnosis['rule_conclusion']}
规则证据：{diagnosis['rule_diagnosis']}
综合置信度：{diagnosis['confidence']}

请决策。"""}
        ]
        result = await self.llm.chat_with_tools(messages, TOOLS_SCHEMA, execute_tool)

        decision = {
            "decision": "告警" if "告警" in result["content"] else "不告警",
            "level": self._extract_level(result["content"]),
            "reason": result["content"],
            "diagnosis": diagnosis,
            "requires_human": False
        }
        if decision["decision"] == "告警":
            self.alarm_history.append(decision)
        return decision

    def _extract_level(self, text: str) -> str:
        for level in ["critical", "warning", "info"]:
            if level in text:
                return level
        return "info"
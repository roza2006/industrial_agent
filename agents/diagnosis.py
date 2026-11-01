# agents/diagnosis.py
from datetime import datetime
from llm_client import LLMClient
from tools import TOOLS_SCHEMA, execute_tool
from rag_knowledge import retrieve_context
from rule_engine import RuleEngine

DIAGNOSIS_SYSTEM = """你是工业设备诊断专家。你会收到一条传感器事件，
请使用工具查询相关历史数据，然后给出诊断意见。

诊断原则：
1. 先调用 query_recent_events 查询该传感器最近事件
2. 如果是夹爪，调用 get_sensor_correlation 分析夹爪与真空发生器的联动
3. 如有异常迹象，调用 query_maintenance_log 查询维修记录
4. 参考知识库中的设备手册和工艺标准

输出要求（必须包含以下字段）：
- 诊断结论: 正常 / 疑似异常 / 异常
- 证据: 具体数据引用
- 置信度: 高 / 中 / 低
- 可能原因: 如异常，给出推断
"""

class DiagnosisAgent:
    def __init__(self, llm: LLMClient, rule_engine: RuleEngine):
        self.llm = llm
        self.rule_engine = rule_engine

    async def run(self, event: dict) -> dict:
        sensor_name = event["sensor_name"]
        if event["new_val"] == 1:
            self.rule_engine.record_action(sensor_name, datetime.now())

        event_desc = f"{sensor_name} 状态变化 {event['old_val']}→{event['new_val']}"
        rag_context = retrieve_context(event_desc)

        messages = [
            {"role": "system", "content": DIAGNOSIS_SYSTEM},
            {"role": "user", "content": f"""事件信息：
- 传感器: {sensor_name}
- 状态变化: {event['old_val']} → {event['new_val']}
- 时间: {event['time']}

知识库参考：
{rag_context}

请诊断。"""}
        ]

        llm_result = await self.llm.chat_with_tools(messages, TOOLS_SCHEMA, execute_tool)
        rule_results = self.rule_engine.evaluate()

        llm_conclusion = self._extract_conclusion(llm_result["content"])
        rule_conclusion = "疑似异常" if rule_results else "正常"
        consistent = (llm_conclusion == rule_conclusion) or (
            llm_conclusion == "正常" and not rule_results
        )

        return {
            "llm_diagnosis": llm_result["content"],
            "rule_diagnosis": rule_results,
            "llm_conclusion": llm_conclusion,
            "rule_conclusion": rule_conclusion,
            "consistent": consistent,
            "confidence": self._calc_confidence(llm_result["content"], consistent),
            "event": event
        }

    def _extract_conclusion(self, text: str) -> str:
        if "疑似异常" in text:
            return "疑似异常"
        if "异常" in text and "正常" not in text:
            return "异常"
        if "正常" in text:
            return "正常"
        return "未知"

    def _calc_confidence(self, text: str, consistent: bool) -> str:
        if "置信度: 高" in text and consistent:
            return "高"
        if "置信度: 低" in text or not consistent:
            return "低"
        return "中"
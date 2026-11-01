# agents/explain.py
from llm_client import LLMClient

EXPLAIN_SYSTEM = """你是工业报告撰写专家。根据诊断和决策结果，
生成一段面向产线主管的自然语言报告。要求：
1. 用通俗语言解释发生了什么
2. 给出可能的原因
3. 给出具体的检查/维修建议
4. 控制在200字以内
"""

class ExplainAgent:
    def __init__(self, llm: LLMClient):
        self.llm = llm

    async def run(self, decision: dict) -> str:
        messages = [
            {"role": "system", "content": EXPLAIN_SYSTEM},
            {"role": "user", "content": f"""诊断:
{decision['diagnosis']['llm_diagnosis']}

决策:
{decision['reason']}"""}
        ]
        result = await self.llm.chat(messages)
        return result["content"]
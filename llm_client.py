# llm_client.py
import json
from typing import Any
from openai import AsyncOpenAI
from config import LLM

class LLMClient:
    def __init__(self):
        if LLM.provider == "deepseek":
            self.client = AsyncOpenAI(
                api_key=LLM.deepseek_api_key,
                base_url=LLM.deepseek_base_url
            )
            self.model = LLM.deepseek_model
        else:
            # 保留原有的 ollama 分支作为备选
            self.client = AsyncOpenAI(api_key="ollama", base_url=LLM.ollama_base_url)
            self.model = LLM.ollama_model

    async def chat(self, messages, tools=None, tool_choice="auto",
                   temperature=0.1, max_tokens=2048) -> dict:
        kwargs: dict[str, Any] = {
            "model": self.model, "messages": messages,
            "temperature": temperature, "max_tokens": max_tokens,
        }
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = tool_choice
        resp = await self.client.chat.completions.create(**kwargs)
        msg = resp.choices[0].message
        return {
            "content": msg.content or "",
            "tool_calls": [
                {"id": tc.id, "name": tc.function.name,
                 "arguments": json.loads(tc.function.arguments)}
                for tc in (msg.tool_calls or [])
            ]
        }

    async def chat_with_tools(self, messages, tools, tool_executor, max_rounds=5) -> dict:
        """ReAct循环：LLM调工具 → 执行 → 结果回传 → 继续推理"""
        for _ in range(max_rounds):
            result = await self.chat(messages, tools=tools)
            if not result["tool_calls"]:
                return result

            messages.append({
                "role": "assistant",
                "content": result["content"],
                "tool_calls": [
                    {"id": tc["id"], "type": "function",
                     "function": {"name": tc["name"],
                                  "arguments": json.dumps(tc["arguments"], ensure_ascii=False)}}
                    for tc in result["tool_calls"]
                ]
            })
            for tc in result["tool_calls"]:
                tool_result = tool_executor(tc["name"], tc["arguments"])
                messages.append({
                    "role": "tool", "tool_call_id": tc["id"],
                    "content": str(tool_result)
                })
        return result
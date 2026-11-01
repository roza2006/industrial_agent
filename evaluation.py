# evaluation.py
import json
import os
from datetime import datetime
from config import CFG, MYSQL
import pymysql

class AgentEvaluator:
    def __init__(self):
        os.makedirs(CFG.trace_dir, exist_ok=True)

    def record_trace(self, event: dict, result: dict):
        """记录到文件和数据库"""
        trace = {
            "timestamp": datetime.now().isoformat(),
            "event": event,
            "diagnosis": result.get("diagnosis"),
            "decision": result.get("decision"),
            "explanation": result.get("explanation"),
        }
        # 写文件
        fn = f"{CFG.trace_dir}/trace_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.json"
        with open(fn, "w", encoding="utf-8") as f:
            json.dump(trace, f, ensure_ascii=False, indent=2, default=str)

        # 写数据库
        try:
            conn = pymysql.connect(**vars(MYSQL))
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO agent_traces
                (trace_time, event_json, diagnosis_json, decision_json, explanation)
                VALUES (NOW(), %s, %s, %s, %s)
            """, (
                json.dumps(event, ensure_ascii=False, default=str),
                json.dumps(result.get("diagnosis"), ensure_ascii=False, default=str),
                json.dumps(result.get("decision"), ensure_ascii=False, default=str),
                result.get("explanation", "")
            ))
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"⚠️ trace入库失败: {e}")

    def compute_metrics(self) -> dict:
        """计算准确率"""
        conn = pymysql.connect(**vars(MYSQL))
        cursor = conn.cursor()
        cursor.execute("""
            SELECT human_feedback, COUNT(*) FROM agent_traces
            WHERE human_feedback IS NOT NULL
            GROUP BY human_feedback
        """)
        rows = dict(cursor.fetchall())
        conn.close()

        total = sum(rows.values())
        if total == 0:
            return {"total": 0, "message": "尚无人工反馈"}

        correct = rows.get("correct", 0)
        return {
            "total": total,
            "correct": correct,
            "wrong": rows.get("wrong", 0),
            "partial": rows.get("partial", 0),
            "accuracy": round(correct / total, 3)
        }


async def run_eval(graph, dataset_path: str) -> dict:
    """跑评测集"""
    with open(dataset_path, encoding="utf-8") as f:
        dataset = json.load(f)

    correct = 0
    results = []
    for case in dataset:
        try:
            result = await graph.ainvoke(case["event"])
            diag = result.get("diagnosis") or {}
            predicted = diag.get("llm_conclusion", "未知")
            expected = case["expected_conclusion"]
            is_ok = (predicted == expected)
            if is_ok:
                correct += 1
            results.append({
                "event": case["event"],
                "expected": expected,
                "predicted": predicted,
                "correct": is_ok
            })
        except Exception as e:
            results.append({"event": case["event"], "error": str(e), "correct": False})

    return {
        "total": len(dataset),
        "correct": correct,
        "accuracy": round(correct / len(dataset), 3) if dataset else 0,
        "results": results
    }
# rule_engine.py
from datetime import datetime
from collections import defaultdict

class RuleEngine:
    def __init__(self):
        self.action_history: dict[str, list[datetime]] = defaultdict(list)
        self.rules = {
            "gripper_max_cycle": 3.5,
            "vacuum_max_delay": 1.5,
            "min_samples": 5,
        }

    def record_action(self, sensor_name: str, timestamp: datetime):
        self.action_history[sensor_name].append(timestamp)
        self.action_history[sensor_name] = self.action_history[sensor_name][-50:]

    def check_gripper_cycle(self) -> dict | None:
        history = self.action_history.get("夹爪", [])
        if len(history) < self.rules["min_samples"]:
            return None
        intervals = [(history[i+1]-history[i]).total_seconds()
                     for i in range(len(history)-1)]
        recent = intervals[-5:]
        avg = sum(recent) / len(recent)
        if avg > self.rules["gripper_max_cycle"]:
            return {
                "rule": "gripper_cycle",
                "conclusion": "疑似异常",
                "evidence": f"夹爪平均节拍{avg:.2f}s，阈值{self.rules['gripper_max_cycle']}s",
                "confidence": "中" if avg < 5.0 else "高",
                "avg_cycle": avg
            }
        return None

    def check_vacuum_delay(self) -> dict | None:
        v = self.action_history.get("真空发生器", [])
        g = self.action_history.get("夹爪", [])
        if not v or not g:
            return None
        delays = []
        for tv in v[-5:]:
            for tg in g:
                if tg > tv and (tg - tv).total_seconds() < 5:
                    delays.append((tg - tv).total_seconds())
                    break
        if not delays:
            return None
        avg = sum(delays) / len(delays)
        if avg > self.rules["vacuum_max_delay"]:
            return {
                "rule": "vacuum_delay",
                "conclusion": "疑似异常",
                "evidence": f"真空→夹爪平均延迟{avg:.2f}s，阈值{self.rules['vacuum_max_delay']}s",
                "confidence": "中",
                "avg_delay": avg
            }
        return None

    def evaluate(self) -> list[dict]:
        results = []
        for check in [self.check_gripper_cycle, self.check_vacuum_delay]:
            r = check()
            if r:
                results.append(r)
        return results
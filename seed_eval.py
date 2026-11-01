# seed_eval.py
"""从模拟数据中抽取50条，自动标注expected_conclusion"""
import json
import random
import pymysql
from config import MYSQL, CFG

def main():
    conn = pymysql.connect(**vars(MYSQL))
    cursor = conn.cursor()

    # 抽正常样本：夹爪节拍在2.0-3.0的
    cursor.execute("""
        SELECT event_time, sensor_name, old_value, new_value
        FROM machine_events
        WHERE machine_id=%s AND sensor_name='夹爪' AND new_value=1
        ORDER BY RAND() LIMIT 25
    """, (CFG.machine_id,))
    normal = cursor.fetchall()

    # 抽异常样本：从异常工况时间段
    cursor.execute("""
        SELECT event_time, sensor_name, old_value, new_value
        FROM machine_events
        WHERE machine_id=%s AND sensor_name='夹爪' AND new_value=1
          AND HOUR(event_time) = 18
        ORDER BY RAND() LIMIT 25
    """, (CFG.machine_id,))
    anomaly = cursor.fetchall()
    conn.close()

    dataset = []
    for t, name, old, new in normal:
        dataset.append({
            "event": {
                "sensor_id": 4, "sensor_name": name,
                "old_val": old, "new_val": new,
                "time": str(t)
            },
            "expected_conclusion": "正常"
        })
    for t, name, old, new in anomaly:
        dataset.append({
            "event": {
                "sensor_id": 4, "sensor_name": name,
                "old_val": old, "new_val": new,
                "time": str(t)
            },
            "expected_conclusion": "疑似异常"
        })

    random.shuffle(dataset)
    with open(CFG.eval_dataset_path, "w", encoding="utf-8") as f:
        json.dump(dataset, f, ensure_ascii=False, indent=2)
    print(f"✅ 评测集已生成: {len(dataset)} 条 → {CFG.eval_dataset_path}")

if __name__ == "__main__":
    main()
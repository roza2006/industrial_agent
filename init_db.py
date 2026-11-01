# init_db.py
import pymysql
from config import MYSQL

DDL = [
    """
    CREATE TABLE IF NOT EXISTS machine_events (
        id INT AUTO_INCREMENT PRIMARY KEY,
        machine_id VARCHAR(50),
        production_date DATE,
        shift VARCHAR(10),
        event_time DATETIME(3),
        sensor_name VARCHAR(50),
        old_value INT,
        new_value INT,
        product_count INT DEFAULT 0,
        INDEX idx_sensor_time (machine_id, sensor_name, event_time)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """,
    """
    CREATE TABLE IF NOT EXISTS alarm_log (
        id INT AUTO_INCREMENT PRIMARY KEY,
        machine_id VARCHAR(50),
        alarm_time DATETIME,
        level VARCHAR(20),
        message TEXT,
        INDEX idx_time (alarm_time)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """,
    """
    CREATE TABLE IF NOT EXISTS maintenance_log (
        id INT AUTO_INCREMENT PRIMARY KEY,
        machine_id VARCHAR(50),
        sensor_name VARCHAR(50),
        maint_time DATETIME,
        description TEXT
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """,
    """
    CREATE TABLE IF NOT EXISTS agent_traces (
        id INT AUTO_INCREMENT PRIMARY KEY,
        trace_time DATETIME,
        event_json TEXT,
        diagnosis_json TEXT,
        decision_json TEXT,
        explanation TEXT,
        human_feedback VARCHAR(20) DEFAULT NULL,
        INDEX idx_time (trace_time)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """,
]

def init():
    conn = pymysql.connect(**vars(MYSQL))
    cursor = conn.cursor()
    for sql in DDL:
        cursor.execute(sql)
    conn.commit()
    conn.close()
    print("✅ 数据库表已初始化")

if __name__ == "__main__":
    init()
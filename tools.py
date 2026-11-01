# tools.py
import pymysql
from config import MYSQL, CFG

def _conn():
    return pymysql.connect(**vars(MYSQL))

def query_recent_events(sensor_name: str, minutes: int = 10) -> str:
    """查询最近N分钟某传感器事件"""
    conn = _conn(); cursor = conn.cursor()
    cursor.execute("""
        SELECT event_time, old_value, new_value, product_count
        FROM machine_events
        WHERE machine_id=%s AND sensor_name=%s
          AND event_time > NOW() - INTERVAL %s MINUTE
        ORDER BY event_time DESC LIMIT 50
    """, (CFG.machine_id, sensor_name, minutes))
    rows = cursor.fetchall(); conn.close()
    if not rows:
        return f"最近{minutes}分钟没有{sensor_name}的事件"
    return "\n".join([f"{r[0]} {r[1]}→{r[2]} 产量+{r[3]}" for r in rows])

def get_sensor_correlation(sensor_a: str, sensor_b: str, minutes: int = 30) -> str:
    """计算两传感器响应延迟"""
    conn = _conn(); cursor = conn.cursor()
    cursor.execute("""
        SELECT event_time, sensor_name, new_value
        FROM machine_events
        WHERE machine_id=%s AND sensor_name IN (%s, %s)
          AND event_time > NOW() - INTERVAL %s MINUTE
        ORDER BY event_time
    """, (CFG.machine_id, sensor_a, sensor_b, minutes))
    rows = cursor.fetchall(); conn.close()
    if len(rows) < 2:
        return f"数据不足"

    times_a = [r[0] for r in rows if r[1] == sensor_a and r[2] == 1]
    times_b = [r[0] for r in rows if r[1] == sensor_b and r[2] == 1]
    if not times_a or not times_b:
        return f"{sensor_a}或{sensor_b}最近{minutes}分钟无动作"

    delays = []
    for ta in times_a:
        for tb in times_b:
            if tb > ta and (tb - ta).total_seconds() < 10:
                delays.append((tb - ta).total_seconds())
                break
    if delays:
        avg = sum(delays) / len(delays)
        return f"{sensor_a}→{sensor_b}平均延迟: {avg:.2f}s (样本:{len(delays)})"
    return f"{sensor_a}和{sensor_b}未检测到有效联动"

def get_production_stats(shift: str = "今日") -> str:
    """产量统计"""
    conn = _conn(); cursor = conn.cursor()
    if shift == "今日":
        cursor.execute("""
            SELECT shift, SUM(product_count) FROM machine_events
            WHERE machine_id=%s AND production_date=CURDATE()
            GROUP BY shift
        """, (CFG.machine_id,))
    else:
        cursor.execute("""
            SELECT SUM(product_count) FROM machine_events
            WHERE machine_id=%s AND production_date=CURDATE() AND shift=%s
        """, (CFG.machine_id, shift))
    rows = cursor.fetchall(); conn.close()
    return str(rows)

def query_maintenance_log(sensor_name: str = None, days: int = 30) -> str:
    """查维修记录"""
    conn = _conn(); cursor = conn.cursor()
    if sensor_name:
        cursor.execute("""
            SELECT maint_time, description FROM maintenance_log
            WHERE machine_id=%s AND sensor_name=%s
              AND maint_time > NOW() - INTERVAL %s DAY
            ORDER BY maint_time DESC LIMIT 10
        """, (CFG.machine_id, sensor_name, days))
    else:
        cursor.execute("""
            SELECT maint_time, sensor_name, description FROM maintenance_log
            WHERE machine_id=%s AND maint_time > NOW() - INTERVAL %s DAY
            ORDER BY maint_time DESC LIMIT 10
        """, (CFG.machine_id, days))
    rows = cursor.fetchall(); conn.close()
    return str(rows) if rows else "无维修记录"

def send_alarm(level: str, message: str) -> str:
    """发送告警"""
    print(f"🚨 [{level}] {message}")
    conn = _conn(); cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO alarm_log (machine_id, alarm_time, level, message)
        VALUES (%s, NOW(), %s, %s)
    """, (CFG.machine_id, level, message))
    conn.commit(); conn.close()
    return f"告警已记录: [{level}] {message}"


TOOLS_SCHEMA = [
    {"type": "function", "function": {
        "name": "query_recent_events",
        "description": "查询最近N分钟某传感器的事件记录",
        "parameters": {"type": "object", "properties": {
            "sensor_name": {"type": "string"},
            "minutes": {"type": "integer"}
        }, "required": ["sensor_name"]}}},
    {"type": "function", "function": {
        "name": "get_sensor_correlation",
        "description": "计算两个传感器的响应延迟，判断联动是否正常",
        "parameters": {"type": "object", "properties": {
            "sensor_a": {"type": "string"},
            "sensor_b": {"type": "string"},
            "minutes": {"type": "integer"}
        }, "required": ["sensor_a", "sensor_b"]}}},
    {"type": "function", "function": {
        "name": "get_production_stats",
        "description": "获取班次产量统计",
        "parameters": {"type": "object", "properties": {
            "shift": {"type": "string", "enum": ["早班","中班","夜班","今日"]}
        }}}},
    {"type": "function", "function": {
        "name": "query_maintenance_log",
        "description": "查询维修记录",
        "parameters": {"type": "object", "properties": {
            "sensor_name": {"type": "string"},
            "days": {"type": "integer"}
        }}}},
    {"type": "function", "function": {
        "name": "send_alarm",
        "description": "发送告警",
        "parameters": {"type": "object", "properties": {
            "level": {"type": "string", "enum": ["info","warning","critical"]},
            "message": {"type": "string"}
        }, "required": ["level", "message"]}}},
]

_TOOL_MAP = {
    "query_recent_events": query_recent_events,
    "get_sensor_correlation": get_sensor_correlation,
    "get_production_stats": get_production_stats,
    "query_maintenance_log": query_maintenance_log,
    "send_alarm": send_alarm,
}

def execute_tool(name: str, args: dict) -> str:
    fn = _TOOL_MAP.get(name)
    if not fn:
        return f"未知工具: {name}"
    try:
        return fn(**args)
    except Exception as e:
        return f"工具执行失败: {e}"
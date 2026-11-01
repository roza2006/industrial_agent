# simulate_data.py
import pymysql
import random
from datetime import datetime, timedelta
from config import MYSQL, CFG

def simulate_normal(start, duration_min=120, cycle_sec=2.5, delay_sec=0.8):
    """正常工况：夹爪2.5s一次，真空到夹爪0.8s"""
    events = []
    t = start
    end = start + timedelta(minutes=duration_min)
    while t < end:
        events.append((t, '真空发生器', 0, 1, 0))
        tg = t + timedelta(seconds=delay_sec + random.uniform(-0.1, 0.1))
        events.append((tg, '夹爪', 0, 1, 1))
        events.append((tg + timedelta(seconds=0.5), '夹爪', 1, 0, 0))
        events.append((t + timedelta(seconds=1.0), '真空发生器', 1, 0, 0))
        t += timedelta(seconds=cycle_sec + random.uniform(-0.2, 0.2))
    return events

def simulate_anomaly(start, duration_min=60, cycle_sec=4.5, delay_sec=2.0):
    """异常工况：夹爪4.5s一次，真空到夹爪2.0s"""
    events = []
    t = start
    end = start + timedelta(minutes=duration_min)
    while t < end:
        events.append((t, '真空发生器', 0, 1, 0))
        tg = t + timedelta(seconds=delay_sec + random.uniform(-0.3, 0.3))
        events.append((tg, '夹爪', 0, 1, 1))
        events.append((tg + timedelta(seconds=0.5), '夹爪', 1, 0, 0))
        events.append((t + timedelta(seconds=1.0), '真空发生器', 1, 0, 0))
        t += timedelta(seconds=cycle_sec + random.uniform(-0.3, 0.3))
    return events

def get_shift(t):
    h = t.hour
    if 8 <= h < 16: return '早班'
    if 16 <= h < 24: return '中班'
    return '夜班'

def insert_events(events):
    conn = pymysql.connect(**vars(MYSQL))
    cursor = conn.cursor()
    sql = """
        INSERT INTO machine_events
        (machine_id, production_date, shift, event_time,
         sensor_name, old_value, new_value, product_count)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """
    for t, name, old, new, prod in events:
        cursor.execute(sql, (
            CFG.machine_id, t.date(), get_shift(t),
            t.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3],
            name, old, new, prod
        ))
    conn.commit()
    conn.close()

def seed_maintenance():
    """造10条维修记录"""
    records = [
        ('真空发生器', '2026-09-15 10:30:00', '更换真空过滤器，滤芯堵塞'),
        ('夹爪',       '2026-09-20 14:00:00', '夹爪气缸密封圈老化，更换'),
        ('真空发生器', '2026-09-28 09:15:00', '气路接头松动，重新紧固'),
        ('摆臂大电机', '2026-09-10 16:20:00', '电机轴承加注润滑脂'),
        ('接近开关',   '2026-09-05 11:00:00', '接近开关位置偏移，重新调整'),
        ('夹爪',       '2026-09-01 08:30:00', '夹爪导轨清洁润滑'),
        ('真空发生器', '2026-08-25 13:00:00', '真空管路检漏，更换密封圈'),
        ('红外漫反射', '2026-08-20 10:00:00', '传感器镜面清洁'),
        ('颜色传感器', '2026-08-15 15:30:00', '传感器校准'),
        ('摆臂大电机', '2026-08-10 09:00:00', '皮带张紧度调整'),
    ]
    conn = pymysql.connect(**vars(MYSQL))
    cursor = conn.cursor()
    for name, t, desc in records:
        cursor.execute("""
            INSERT INTO maintenance_log
            (machine_id, sensor_name, maint_time, description)
            VALUES (%s, %s, %s, %s)
        """, (CFG.machine_id, name, t, desc))
    conn.commit()
    conn.close()
    print(f"✅ 已插入 {len(records)} 条维修记录")

def main():
    print("开始生成30天模拟数据...")
    base = datetime.now() - timedelta(days=30)
    for day in range(30):
        d = base + timedelta(days=day)
        # 早班：正常
        insert_events(simulate_normal(d.replace(hour=8, minute=0), 120))
        # 中班：前2小时正常，后1小时异常
        mid = d.replace(hour=16, minute=0)
        insert_events(simulate_normal(mid, 120))
        insert_events(simulate_anomaly(mid + timedelta(hours=2), 60))
        # 夜班：正常
        night = d.replace(hour=0, minute=0) + timedelta(days=1)
        insert_events(simulate_normal(night, 120))
        if day % 5 == 0:
            print(f"  已生成 {day+1}/30 天")

    seed_maintenance()
    print("✅ 模拟数据生成完成")

if __name__ == "__main__":
    main()
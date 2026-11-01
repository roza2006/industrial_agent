# main.py
import asyncio
import json
import sys
import random
import pymysql
from datetime import datetime
from asyncua import Server
from config import CFG, MYSQL, LLM
from graph import IndustrialAgentGraph
from evaluation import AgentEvaluator, run_eval
from serial_bridge import serial_reader


async def simulated_serial_source(queue: asyncio.Queue):
    """无串口时，模拟产线数据源"""
    print("🎮 使用模拟数据源（无串口模式）")
    sensors = [1, 2, 3, 4, 5, 6]
    while True:
        await asyncio.sleep(2.5)  # 正常节拍
        data = {f"n{i}": 0 for i in sensors}
        # 真空先动作
        data["n3"] = 1
        await queue.put(data)
        await asyncio.sleep(0.8)

        # 夹爪动作（20% 概率模拟异常）
        if random.random() < 0.2:
            await asyncio.sleep(1.2)  # 异常：延迟变大
        data = {f"n{i}": 0 for i in sensors}
        data["n3"] = 0
        data["n4"] = 1
        await queue.put(data)

        # 夹爪复位
        await asyncio.sleep(0.5)
        data["n4"] = 0
        await queue.put(data)
        await asyncio.sleep(0.3)


async def run_agent(graph: IndustrialAgentGraph, evaluator: AgentEvaluator, event: dict):
    """异步运行Agent，不阻塞主循环"""
    try:
        result = await graph.ainvoke(event)
        evaluator.record_trace(event, result)

        if result.get("explanation"):
            print(f"\n{'='*60}")
            print(f"📋 Agent报告 [{event['sensor_name']}]")
            print(f"{'='*60}")
            print(result["explanation"])
            print(f"{'='*60}\n")
        if result.get("error"):
            print(f"⚠️ {result['error']}")
    except Exception as e:
        print(f"❌ Agent执行失败: {e}")


async def main(use_sim: bool = False):
    """主程序，use_sim=True 时使用模拟数据源"""
    loop = asyncio.get_running_loop()

    # 1. MySQL
    conn = pymysql.connect(**vars(MYSQL))
    cursor = conn.cursor()
    print("✅ MySQL 已连接")

    # 2. OPC UA
    server = Server()
    await server.init()
    server.set_endpoint(CFG.opcua_endpoint)
    idx = await server.register_namespace("http://machine.local")
    opcua_nodes = {}
    for i in range(1, 7):
        node = await server.nodes.objects.add_variable(idx, f"Node{i}", False)
        await node.set_writable()
        opcua_nodes[i] = node
    print(f"✅ OPC UA 已启动: {CFG.opcua_endpoint}")

    # 3. Agent图
    agent_graph = IndustrialAgentGraph()
    evaluator = AgentEvaluator()
    model_name = LLM.deepseek_model if LLM.provider == "deepseek" else LLM.ollama_model
    print(f"✅ 多Agent图已构建 (LLM: {LLM.provider}/{model_name})")

    # 4. 数据源
    data_queue = asyncio.Queue()
    if use_sim:
        asyncio.create_task(simulated_serial_source(data_queue))
    else:
        loop.run_in_executor(None, serial_reader, data_queue, loop)

    last_state = {i: 0 for i in range(1, 7)}
    print("🚀 系统就绪，等待数据...\n")

    async with server:
        while True:
            try:
                data = await asyncio.wait_for(data_queue.get(), timeout=0.5)
            except asyncio.TimeoutError:
                continue

            for i in range(1, 7):
                key = f"n{i}"
                if key not in data:
                    continue
                new_val = int(data[key])
                old_val = last_state[i]
                if new_val == old_val:
                    continue

                await opcua_nodes[i].write_value(bool(new_val))

                if new_val == 1:
                    cursor.execute("""
                        INSERT INTO machine_events
                        (machine_id, production_date, shift, event_time,
                         sensor_name, old_value, new_value, product_count)
                        VALUES (%s, CURDATE(), '早班', NOW(), %s, %s, %s, %s)
                    """, (CFG.machine_id, CFG.sensor_names[i], old_val, new_val,
                          1 if i in CFG.production_sensors else 0))
                    conn.commit()

                    event = {
                        "sensor_id": i,
                        "sensor_name": CFG.sensor_names[i],
                        "old_val": old_val,
                        "new_val": new_val,
                        "time": datetime.now().isoformat()
                    }
                    asyncio.create_task(run_agent(agent_graph, evaluator, event))

                last_state[i] = new_val


async def run_eval_mode():
    """评测模式"""
    graph = IndustrialAgentGraph()
    print("📊 开始评测...")
    result = await run_eval(graph, CFG.eval_dataset_path)
    print(f"\n准确率: {result['accuracy']:.1%} ({result['correct']}/{result['total']})")
    for r in result["results"][:5]:
        print(f"  {r}")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "eval":
        asyncio.run(run_eval_mode())
    elif len(sys.argv) > 1 and sys.argv[1] == "sim":
        print("=" * 60)
        print("  工业多Agent智能诊断系统 (模拟模式)")
        print("=" * 60)
        asyncio.run(main(use_sim=True))
    else:
        print("=" * 60)
        print("  工业多Agent智能诊断系统")
        print("=" * 60)
        asyncio.run(main(use_sim=False))
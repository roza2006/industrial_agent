工业多Agent系统测试 SOP
环境：Windows + PowerShell + MySQL 3307 + DeepSeek API
项目路径：E:\industrial_agent

一、每次开机后的启动流程
1.1 环境检查（30秒）
powershell
# 进入项目目录
cd E:\industrial_agent

# 检查 MySQL 服务是否运行
Get-Service -Name MySQL80
# 期望：Status = Running，如果是 Stopped，先启动：
net start MySQL80

# 检查端口 3307 是否在监听
netstat -ano | findstr "3307"
# 期望：看到 0.0.0.0:3307 LISTENING
1.2 设置环境变量（每个新 PowerShell 窗口都要设）
powershell
$env:DEEPSEEK_API_KEY="sk-你的DeepSeekAPIKey"
$env:MYSQL_PASSWORD="你的MySQL密码"
$env:HF_ENDPOINT="https://hf-mirror.com"    # 可选，加速模型下载
1.3 验证配置
powershell
python -c "from config import MYSQL, LLM; print('MySQL:', vars(MYSQL)['port']); print('LLM:', LLM.provider, LLM.deepseek_model)"
期望输出：

text
MySQL: 3307
LLM: deepseek deepseek-flash
二、首次部署流程（只跑一次）
powershell
# 1. 建表
python init_db.py
# 期望：✅ 数据库表已初始化

# 2. 灌模拟数据（30天历史）
python simulate_data.py
# 期望：✅ 模拟数据生成完成

# 3. 导入知识库
python seed_knowledge.py
# 期望：✅ 知识库导入完成（首次会下载 embedding 模型约100MB）

# 4. 生成评测集
python seed_eval.py
# 期望：✅ 评测集已生成: 50 条
验证数据库：

powershell
& "C:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe" -u root -p -P 3307 -e "USE machine_data; SHOW TABLES; SELECT COUNT(*) FROM machine_events;"
期望：4 张表 + machine_events 有几万条。

三、日常测试流程
3.1 快速验证（改代码后先跑这个）
powershell
python main.py eval
做什么：用 50 条评测集跑完整 Agent 链路（诊断→决策→解释），输出准确率。

期望输出：

text
📊 开始评测...
...
准确率: 75.0% (38/50)
看什么：

准确率 > 70% → Agent 逻辑正常

准确率 < 50% → Prompt 或工具查询有问题

3.2 实时模拟（不接硬件）
powershell
python main.py sim
做什么：模拟产线数据，每 2.5 秒触发一次夹爪事件，20% 概率异常。

看什么：

控制台是否持续输出 📡 传感器名 0→1

有异常时是否输出 📋 Agent报告

按 Ctrl+C 停止

建议：跑 5-10 分钟观察，不要长时间跑（每小时约 10 元 DeepSeek 费用）。

3.3 真实硬件
powershell
# 先确认 config.py 里 serial_port 是实际串口号
python -c "from config import CFG; print(CFG.serial_port)"
powershell
python main.py
看什么：

✅ 串口 COMxx 已打开

硬件触发时是否有 📡 输出

Agent 是否触发

四、数据管理
4.1 清空重来（常见需求）
powershell
# 清空事件表（保留表结构）
& "C:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe" -u root -p -P 3307 -e "USE machine_data; TRUNCATE TABLE machine_events; TRUNCATE TABLE maintenance_log; TRUNCATE TABLE alarm_log; TRUNCATE TABLE agent_traces;"

# 重新灌数据
python simulate_data.py
4.2 只清空 Agent 记录（保留传感器数据）
powershell
& "C:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe" -u root -p -P 3307 -e "USE machine_data; TRUNCATE TABLE agent_traces; TRUNCATE TABLE alarm_log;"
4.3 查看数据
powershell
# 事件数量
& "C:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe" -u root -p -P 3307 -e "USE machine_data; SELECT COUNT(*) FROM machine_events;"

# 最近5条告警
& "C:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe" -u root -p -P 3307 -e "USE machine_data; SELECT * FROM alarm_log ORDER BY id DESC LIMIT 5;"

# 最近5条 Agent 决策
& "C:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe" -u root -p -P 3307 -e "USE machine_data; SELECT trace_time, LEFT(explanation, 100) FROM agent_traces ORDER BY id DESC LIMIT 5;"
4.4 备份数据
powershell
& "C:\Program Files\MySQL\MySQL Server 8.0\bin\mysqldump.exe" -u root -p -P 3307 machine_data > backup_20261005.sql
五、常见错误处理
错误 1：Can't connect to MySQL server
原因：MySQL 服务没启动，或端口不对。

powershell
# 检查服务
Get-Service -Name MySQL80

# 检查端口
netstat -ano | findstr "3307"
修复：net start MySQL80，或改 config.py 里的 port。

错误 2：Access denied for user 'root'
原因：密码错误。

powershell
# 验证密码
python -c "import pymysql; from config import MYSQL; pymysql.connect(**vars(MYSQL)); print('OK')"
修复：改 config.py 里的 password。

错误 3：ModuleNotFoundError: No module named 'xxx'
原因：包没装。

powershell
pip install 包名
一次性装齐：

powershell
pip install openai pymysql pyserial asyncua langgraph langchain langchain-community langchain-text-splitters chromadb pypdf
错误 4：ImportError: cannot import name 'IndustrialAgentGraph'
原因：graph.py 内容不完整。

修复：用完整版替换 graph.py（含 IndustrialAgentGraph 类）。

错误 5：Table 'machine_data.machine_events' doesn't exist
原因：init_db.py 没成功跑。

修复：

powershell
python init_db.py
# 或
python -c "import init_db; init_db.init()"
错误 6：Agent 报告说"数据不足"或"无法验证"
原因：工具查询用 NOW()，但评测事件是 30 天前的。

临时方案：忽略，看准确率。
根本方案：修改 tools.py，让查询支持相对事件时间（见之前讨论）。

错误 7：DeepSeek API 报错 401 / 402
401：API Key 错误 → 检查 $env:DEEPSEEK_API_KEY

402：余额不足 → 去 DeepSeek 平台充值

错误 8：DeprecationWarning: 'db' is deprecated
不影响运行，忽略。想消除就改 config.py：

python
database: str = "machine_data"    # 原来是 db
错误 9：PowerShell 里跑 mysql 提示找不到命令
用完整路径：

powershell
& "C:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe" -u root -p -P 3307 -e "..."
或永久加环境变量：

powershell
[Environment]::SetEnvironmentVariable("Path", [Environment]::GetEnvironmentVariable("Path", "User") + ";C:\Program Files\MySQL\MySQL Server 8.0\bin", "User")
错误 10：python main.py 卡住不动
原因：串口没数据，或串口号错误。

powershell
# 检查串口配置
python -c "from config import CFG; print(CFG.serial_port)"

# 无硬件时改用模拟模式
python main.py sim
六、参数调整速查
6.1 影响 Agent 诊断的
参数	文件	位置	说明
gripper_max_cycle	rule_engine.py	self.rules	夹爪最大节拍（默认3.5s）
vacuum_max_delay	rule_engine.py	self.rules	真空最大延迟（默认1.5s）
min_samples	rule_engine.py	self.rules	最少样本数（默认5）
DIAGNOSIS_SYSTEM	agents/diagnosis.py	顶部	诊断 Prompt
DECISION_SYSTEM	agents/decision.py	顶部	决策 Prompt
EXPLAIN_SYSTEM	agents/explain.py	顶部	解释 Prompt
6.2 影响系统连接的
参数	文件	位置	说明
serial_port	config.py	SystemConfig	串口号
port	config.py	MySQLConfig	MySQL端口（你的是3307）
password	config.py	MySQLConfig	MySQL密码
deepseek_api_key	环境变量	-	API Key
deepseek_model	config.py	LLMConfig	模型名（deepseek-flash）
6.3 影响模拟数据的
参数	文件	位置	说明
cycle_sec	simulate_data.py	simulate_normal	正常节拍（默认2.5s）
delay_sec	simulate_data.py	simulate_normal	正常延迟（默认0.8s）
cycle_sec	simulate_data.py	simulate_anomaly	异常节拍（默认4.5s）
delay_sec	simulate_data.py	simulate_anomaly	异常延迟（默认2.0s）
七、比赛/演示专用 SOP
7.1 演示前 1 天
powershell
# 1. 清空旧数据，重新灌
python simulate_data.py

# 2. 跑评测，确认准确率
python main.py eval
# 要求：准确率 > 75%

# 3. 录制备份视频
# 打开录屏软件，跑 python main.py sim，录 5-10 分钟

# 4. 备份数据库
& "C:\Program Files\MySQL\MySQL Server 8.0\bin\mysqldump.exe" -u root -p -P 3307 machine_data > backup_before_demo.sql
7.2 演示当天
开场前（提前30分钟）：

powershell
# 1. 检查环境
Get-Service MySQL80
netstat -ano | findstr "3307"
python -c "from config import MYSQL, LLM; print('OK')"

# 2. 清空 Agent 记录（保留传感器数据）
& "C:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe" -u root -p -P 3307 -e "USE machine_data; TRUNCATE TABLE agent_traces; TRUNCATE TABLE alarm_log;"

# 3. 准备两个终端
# 终端1：跑主程序
# 终端2：准备看数据库
演示中：

powershell
# 终端1：启动模拟模式
python main.py sim

# 终端2：实时查看 Agent 输出
& "C:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe" -u root -p -P 3307 -e "USE machine_data; SELECT trace_time, LEFT(explanation,150) FROM agent_traces ORDER BY id DESC LIMIT 3;"
演示后：

powershell
# 展示统计
& "C:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe" -u root -p -P 3307 -e "USE machine_data; SELECT COUNT(*) FROM agent_traces; SELECT level, COUNT(*) FROM alarm_log GROUP BY level;"
7.3 演示话术
"系统接收串口数据，写入 MySQL 并同步 OPC UA。当传感器动作触发时，LLM Agent 自主调用工具查询历史数据、分析传感器联动、查询维修记录，然后给出诊断、决策和自然语言报告。整个过程全自动，无人干预。"

八、成本控制
操作	预估成本
跑一次 python main.py eval（50条）	~0.5 元
跑 10 分钟 python main.py sim	~1.5-3 元
跑 1 小时 python main.py sim	~10-20 元
跑一天 python main.py sim	~250-500 元
省钱技巧：

测试放在空闲时段（晚上、周末），DeepSeek 价格减半

保持 Prompt 前缀稳定，提高缓存命中率

不要长时间跑 main.py sim，观察 10 分钟足够

用 python main.py eval 代替 sim 做回归测试

九、一键检查脚本（建议保存）
把下面保存为 check.ps1：

powershell
Write-Host "=== 环境检查 ===" -ForegroundColor Cyan

# MySQL 服务
$svc = Get-Service -Name MySQL80 -ErrorAction SilentlyContinue
if ($svc.Status -eq "Running") {
    Write-Host "✅ MySQL 服务: Running" -ForegroundColor Green
} else {
    Write-Host "❌ MySQL 服务未运行，请执行: net start MySQL80" -ForegroundColor Red
}

# 端口
$port = netstat -ano | findstr "3307"
if ($port) {
    Write-Host "✅ 端口 3307 已监听" -ForegroundColor Green
} else {
    Write-Host "❌ 端口 3307 未监听" -ForegroundColor Red
}

# 配置
python -c "from config import MYSQL, LLM; print(f'✅ MySQL: {MYSQL.host}:{MYSQL.port}'); print(f'✅ LLM: {LLM.provider} / {LLM.deepseek_model}')"

# 数据
& "C:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe" -u root -p -P 3307 -e "USE machine_data; SELECT CONCAT('✅ machine_events: ', COUNT(*), ' 条') FROM machine_events; SELECT CONCAT('✅ agent_traces: ', COUNT(*), ' 条') FROM agent_traces;"

Write-Host "`n=== 检查完成 ===" -ForegroundColor Cyan
运行：

powershell
.\check.ps1
十、紧急恢复
如果一切乱了：

powershell
# 1. 清空所有表
& "C:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe" -u root -p -P 3307 -e "USE machine_data; TRUNCATE TABLE machine_events; TRUNCATE TABLE maintenance_log; TRUNCATE TABLE alarm_log; TRUNCATE TABLE agent_traces;"

# 2. 重建
python init_db.py
python simulate_data.py
python seed_knowledge.py
python seed_eval.py

# 3. 验证
python main.py eval
如果代码乱了：从备份或版本控制恢复。

把这份 SOP 保存到 E:\industrial_agent\SOP.md，以后照着做就行。 遇到 SOP 里没写的问题，把报错贴给我。
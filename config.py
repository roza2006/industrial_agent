# config.py
"""全局配置。

API Key 和数据库密码不放代码里，统一从环境变量读，本地可以用 .env。

优先级：环境变量 > 根目录 .env > config_local.py（本地覆盖，不入库）
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field


def _load_dotenv(path: str = ".env") -> None:
    """极简 .env 加载器，避免引入额外依赖。已存在的环境变量优先。"""
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_dotenv()


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    try:
        return int(raw)
    except ValueError:
        return default


@dataclass
class LLMConfig:
    provider: str = os.getenv("LLM_PROVIDER", "deepseek")
    deepseek_api_key: str = os.getenv("DEEPSEEK_API_KEY", "")
    deepseek_base_url: str = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
    deepseek_model: str = os.getenv("DEEPSEEK_MODEL", "deepseek-flash")
    ollama_base_url: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
    ollama_model: str = os.getenv("OLLAMA_MODEL", "qwen2.5:7b")


@dataclass
class MySQLConfig:
    host: str = os.getenv("MYSQL_HOST", "127.0.0.1")
    port: int = field(default_factory=lambda: _env_int("MYSQL_PORT", 3307))
    user: str = os.getenv("MYSQL_USER", "root")
    password: str = os.getenv("MYSQL_PASSWORD", "")
    database: str = os.getenv("MYSQL_DATABASE", "machine_data")
    charset: str = "utf8mb4"


@dataclass
class SystemConfig:
    serial_port: str = os.getenv("SERIAL_PORT", "COM19")
    baud_rate: int = field(default_factory=lambda: _env_int("SERIAL_BAUD", 115200))
    opcua_endpoint: str = os.getenv("OPCUA_ENDPOINT", "opc.tcp://0.0.0.0:4840")
    machine_id: str = os.getenv("MACHINE_ID", "F407_Line1")
    chroma_persist_dir: str = os.getenv("CHROMA_DIR", "./chroma_db")
    knowledge_dir: str = os.getenv("KNOWLEDGE_DIR", "./knowledge")
    eval_dataset_path: str = os.getenv("EVAL_DATASET", "./eval_dataset.json")
    trace_dir: str = os.getenv("TRACE_DIR", "./agent_traces")
    sensor_names: dict = field(default_factory=lambda: {
        1: '接近开关', 2: '摆臂大电机', 3: '真空发生器',
        4: '夹爪', 5: '红外漫反射', 6: '颜色传感器'
    })
    production_sensors: set = field(default_factory=lambda: {4})


CFG = SystemConfig()
MYSQL = MySQLConfig()
LLM = LLMConfig()

# 本地私密覆盖（config_local.py 已被 .gitignore 忽略，不会进入仓库）
try:
    from config_local import apply_local_overrides  # type: ignore
except ImportError:
    pass
else:
    apply_local_overrides(LLM, MYSQL, CFG)

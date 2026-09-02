"""全局配置：数据源、网关、阈值、调度"""
import os

# ========== 数据源模式 ==========
# mock      : 开箱演示模式，内置3个演示ASIN，模拟波动，无需任何key（默认）
# import    : 快照全部来自页面「导入JSON」（我代取真实数据后用），run_all不做事
# gateway   : 网站自动调统一契约网关（中台工具网关/三方API，需填下方GATEWAY_URL）
DATA_SOURCE = os.getenv("MONITOR_SOURCE", "mock")

# ========== 网关模式必填（gateway 才需要） ==========
# POST {GATEWAY_URL}/v1/asin/fields
# body: {"marketplace":"US","asins":["B0FYP2YXZF"]}
GATEWAY_URL = os.getenv("GATEWAY_URL", "")   # 如 https://gateway.example.com
GATEWAY_KEY = os.getenv("GATEWAY_KEY", "")

# ========== 定时巡检（服务器本地时间） ==========
SCHEDULE_HOURS = "9,21"
DB_PATH = os.path.join(os.path.dirname(__file__), "monitor.db")

# ========== 异常阈值（可调） ==========
PRICE_ABS_THRESHOLD = 5.0      # 价格绝对变化 ≥ $5 告警
PRICE_RATE_THRESHOLD = 0.05    # 或相对变化 ≥ 5% 告警
RATING_DROP_THRESHOLD = 0.1    # 评分单日下降 ≥ 0.1 告警
RATING_FLOOR = 4.0             # 评分跌破 4.0 告警
REVIEW_DROP_THRESHOLD = 5      # 评论数单日下降 ≥ 5 告警（疑似删评）

# ========== 演示种子 ==========
SEED_ASINS = [
    {"asin": "B0FYP2YXZF", "note": "演示-端桌套装"},
    {"asin": "B0HHF7PPQT", "note": "演示-床头柜"},
    {"asin": "B0DEMO00001", "note": "演示-自动生成"},
]
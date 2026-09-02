"""数据源适配器：mock（演示）/ gateway（网关自动拉取）/ import（由页面导入驱动）"""
import random
from config import DATA_SOURCE

# ---------------- MOCK 基线数据 ----------------
MOCK_BASE = {
    "B0FYP2YXZF": {
        "title": "LITTLE TREE Solid Wood End Table Set 2 with 2 Drawers & Open Shelf, "
                 "Vintage Brown Couch Side Tables, Nightstand for Bedroom",
        "price": 341.99, "buybox_seller": "Amazon", "sellers_count": 1,
        "rating": 4.7, "review_count": 32},
    "B0HHF7PPQT": {
        "title": "LITTLE TREE 3 Drawers Nightstand, Farmhouse Oversized Bedside Table, Brown",
        "price": 199.99, "buybox_seller": "Amazon", "sellers_count": 1,
        "rating": 4.5, "review_count": 28},
}

def _mock_fetch(asin):
    """演示：对已知ASIN基于基线小幅波动；未知ASIN生成随机演示数据"""
    if asin in MOCK_BASE:
        d = dict(MOCK_BASE[asin])
    else:
        d = {"title": f"Demo Product {asin} (mock)",
             "price": round(random.uniform(60, 260), 2),
             "buybox_seller": random.choice(["Amazon", "Samsung", "FBA Seller"]),
             "sellers_count": random.randint(1, 3),
             "rating": round(random.uniform(4.0, 4.8), 1),
             "review_count": random.randint(10, 200)}
    if random.random() < 0.55:
        d["price"] = round(max(9.99, d["price"] + random.uniform(-12, 12)), 2)
    if random.random() < 0.12:
        d["rating"] = round(max(3.5, d["rating"] - random.uniform(0.05, 0.25)), 2)
    if random.random() < 0.10:
        d["review_count"] = max(0, d["review_count"] - random.randint(2, 8))
    if random.random() < 0.08:
        d["buybox_seller"] = "Another Seller"
        d["sellers_count"] = max(2, d["sellers_count"] + 1)
    return d

def _gateway_fetch(asins):
    """网关模式：调统一契约网关批量拉字段。
    需安装 httpx；如你的网关协议不同，只改这个函数即可。"""
    import httpx
    from config import GATEWAY_URL, GATEWAY_KEY
    if not GATEWAY_URL:
        raise RuntimeError("GATEWAY_URL 未配置，请先开通网关或改用 import/mock 模式")
    r = httpx.post(f"{GATEWAY_URL}/v1/asin/fields",
                   json={"marketplace": "US", "asins": asins},
                   headers={"Authorization": f"Bearer {GATEWAY_KEY}"}, timeout=180)
    r.raise_for_status()
    out = {}
    for it in r.json().get("data", []):
        a = it["asin"]
        out[a] = {
            "asin": a,
            "title": it.get("title", ""),
            "price": float(it.get("price") or 0),
            "buybox_seller": it.get("buyboxSeller") or it.get("sellerName") or "",
            "sellers_count": int(it.get("sellers") or it.get("sellersCount") or 1),
            "rating": float(it.get("rating") or 0),
            "review_count": int(it.get("ratings") or it.get("reviewCount") or 0),
            "url": it.get("url", ""),
        }
    return out

def fetch_all(asins):
    """统一入口：返回 {asin: 标准字段dict}"""
    if DATA_SOURCE == "gateway":
        return _gateway_fetch(asins)
    if DATA_SOURCE == "mock":
        return {a: _mock_fetch(a) for a in asins}
    return {}   # import 模式：不自动拉取，数据来自 /api/import
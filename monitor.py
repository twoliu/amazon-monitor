"""巡检核心：快照入库 + 与上一份 diff + 告警规则"""
import json
from db import get_conn
from adapter import fetch_all
from config import (PRICE_ABS_THRESHOLD, PRICE_RATE_THRESHOLD,
                    RATING_DROP_THRESHOLD, RATING_FLOOR,
                    REVIEW_DROP_THRESHOLD)

def latest_snapshot(asin):
    with get_conn() as c:
        row = c.execute(
            "SELECT * FROM snapshots WHERE asin=? ORDER BY id DESC LIMIT 1",
            (asin,)).fetchone()
    return dict(row) if row else None

def _num(s):
    try:
        return float(s)
    except (TypeError, ValueError):
        return None

def compare_and_alert(asin, prev, cur):
    """逐字段 diff，产出 (diff_list, alert_list)"""
    diffs, alerts = [], []

    if prev["title"] != cur["title"]:
        diffs.append(("title", prev["title"], cur["title"], "P0"))
        alerts.append((f"标题变更！\n旧: {str(prev['title'])[:60]}...\n新: {str(cur['title'])[:60]}...", "P0"))

    old_p, new_p = _num(prev["price"]), _num(cur["price"])
    if old_p is not None and new_p is not None and old_p != new_p:
        delta = new_p - old_p
        rate = abs(delta / old_p) if old_p else 0
        if abs(delta) >= PRICE_ABS_THRESHOLD or rate >= PRICE_RATE_THRESHOLD:
            diffs.append(("price", old_p, new_p, "P1"))
            alerts.append((f"价格变动 {delta:+.2f} ({delta/old_p*100:+.1f}%): "
                           f"${old_p:.2f} → ${new_p:.2f}", "P1"))
        else:
            diffs.append(("price", old_p, new_p, "P3"))

    if prev.get("buybox_seller") != cur.get("buybox_seller"):
        diffs.append(("buybox_seller", prev.get("buybox_seller"), cur.get("buybox_seller"), "P0"))
        alerts.append((f"购物车归属变化: {prev.get('buybox_seller')} → {cur.get('buybox_seller')}", "P0"))
    elif prev.get("sellers_count") != cur.get("sellers_count"):
        diffs.append(("sellers_count", prev.get("sellers_count"), cur.get("sellers_count"), "P1"))
        alerts.append((f"卖家数变化: {prev.get('sellers_count')} → {cur.get('sellers_count')}", "P1"))

    old_r, new_r = _num(prev.get("rating")), _num(cur.get("rating"))
    if old_r is not None and new_r is not None and old_r != new_r:
        if new_r < old_r - RATING_DROP_THRESHOLD or new_r < RATING_FLOOR:
            diffs.append(("rating", old_r, new_r, "P1"))
            alerts.append((f"评分下降: {old_r} → {new_r}", "P1"))

    old_c, new_c = _num(prev.get("review_count")), _num(cur.get("review_count"))
    if old_c is not None and new_c is not None and old_c != new_c:
        if new_c < old_c - REVIEW_DROP_THRESHOLD:
            diffs.append(("review_count", old_c, new_c, "P1"))
            alerts.append((f"评论数异常下降 {old_c:.0f} → {new_c:.0f}（疑似删评）", "P1"))
        elif new_c > old_c:
            diffs.append(("review_count", old_c, new_c, "P3"))

    with get_conn() as c:
        for field, old_v, new_v, sev in diffs:
            c.execute("""INSERT INTO diffs(asin, field, old_value, new_value, severity)
                         VALUES(?,?,?,?,?)""",
                      (asin, field, str(old_v), str(new_v), sev))
        for msg, sev in alerts:
            c.execute("INSERT INTO alerts(asin, message, severity) VALUES(?,?,?)",
                      (asin, msg, sev))
    return diffs, alerts

def ingest(asin, fields):
    """核心入口：ASIN + 标准字段 → 存快照 → 与上一份比对 → 返回结果。
    import 与 gateway 两种模式共用。"""
    cur = {k: fields.get(k) for k in (
        "title", "price", "buybox_seller", "sellers_count",
        "rating", "review_count")}
    prev = latest_snapshot(asin)
    with get_conn() as c:
        c.execute("""INSERT INTO snapshots(asin, title, price, buybox_seller,
                     sellers_count, rating, review_count, raw)
                     VALUES(?,?,?,?,?,?,?,?)""",
                  (asin, cur["title"], cur["price"], cur.get("buybox_seller"),
                   cur.get("sellers_count"), cur.get("rating"),
                   cur.get("review_count"), json.dumps(fields)))
    alerts = []
    if prev:
        _, alerts = compare_and_alert(asin, prev, cur)
    return {"asin": asin, "snapshot": cur, "is_first": not prev, "alerts": alerts}

def run_all():
    """手动/定时巡检入口：按数据源模式分发"""
    from config import DATA_SOURCE, SEED_ASINS
    with get_conn() as c:
        rows = c.execute("SELECT asin FROM monitor_links WHERE enabled=1").fetchall()
    asins = [r["asin"] for r in rows]
    if DATA_SOURCE == "import":
        return []                       # import 模式：由页面导入驱动
    if DATA_SOURCE == "mock":
        seed = {s["asin"] for s in SEED_ASINS}
        asins = [a for a in asins if a in seed]   # mock 只演示种子，不污染导入的真实数据
    fetched = fetch_all(asins)
    return [ingest(a, fetched[a]) for a in asins if a in fetched]
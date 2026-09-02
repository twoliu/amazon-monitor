"""FastAPI 入口：页面 + API + 导入端点 + 定时"""
import os, threading
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import db, monitor
from config import SCHEDULE_HOURS, SEED_ASINS, DATA_SOURCE

db.init_db()
db.seed_links(SEED_ASINS)

app = FastAPI(title="Amazon Link Monitor MVP")
os.makedirs("static", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

# ---------- 定时巡检 ----------
def _schedule():
    try:
        from apscheduler.schedulers.background import BackgroundScheduler
        sched = BackgroundScheduler()
        for h in SCHEDULE_HOURS.split(","):
            sched.add_job(monitor.run_all, "cron", hour=int(h), minute=0)
        sched.start()
    except Exception as e:
        print("[scheduler fallback]", e)
        def loop():
            import time
            while True:
                try:
                    monitor.run_all()
                except Exception as ex:
                    print("[run_all]", ex)
                time.sleep(6 * 3600)
        threading.Thread(target=loop, daemon=True).start()

_schedule()

# ---------- 页面 ----------
@app.get("/", response_class=HTMLResponse)
def index():
    with open(os.path.join("static", "index.html"), encoding="utf-8") as f:
        return f.read()

# ---------- API ----------
@app.get("/api/config")
def api_config():
    return JSONResponse({"data_source": DATA_SOURCE})

@app.post("/api/monitor/run")
def api_run():
    results = monitor.run_all()
    return JSONResponse({"count": len(results), "results": results})

class ImportReq(BaseModel):
    snapshots: list = []

@app.post("/api/import")
async def api_import(req: ImportReq):
    """导入一次巡检快照（我代取真实数据后导出的 JSON）。与模式无关，总是可用。"""
    results = []
    for s in req.snapshots:
        asin = str(s.get("asin", "")).upper().strip()
        if not asin:
            continue
        with db.get_conn() as c:
            c.execute("INSERT OR IGNORE INTO monitor_links(asin) VALUES(?)", (asin,))
        fields = {
            "asin": asin,
            "title": s.get("title", ""),
            "price": float(s.get("price") or 0),
            "buybox_seller": s.get("buyboxSeller") or s.get("sellerName") or "",
            "sellers_count": int(s.get("sellers") or s.get("sellersCount") or 1),
            "rating": float(s.get("rating") or 0),
            "review_count": int(s.get("ratings") or s.get("reviewCount") or 0),
            "url": s.get("url", ""),
        }
        results.append(monitor.ingest(asin, fields))
    return {"count": len(results), "results": results}

@app.get("/api/links")
def api_links():
    with db.get_conn() as c:
        rows = c.execute("SELECT asin, note, enabled, created_at FROM monitor_links").fetchall()
        out = []
        for r in rows:
            s = c.execute("""SELECT title, price, buybox_seller, sellers_count,
                                    rating, review_count, fetched_at
                             FROM snapshots WHERE asin=? ORDER BY id DESC LIMIT 1""",
                          (r["asin"],)).fetchone()
            a = c.execute("""SELECT COUNT(*) n FROM alerts
                             WHERE asin=? AND is_read=0""", (r["asin"],)).fetchone()
            item = {"asin": r["asin"], "note": r["note"], "enabled": r["enabled"],
                    "unread_alerts": a["n"] if a else 0}
            if s:
                item.update(dict(s))
            out.append(item)
    return JSONResponse(out)

@app.get("/api/links/{asin}/history")
def api_history(asin: str):
    with db.get_conn() as c:
        snaps = c.execute("""SELECT fetched_at, title, price, buybox_seller,
                                    sellers_count, rating, review_count
                             FROM snapshots WHERE asin=? ORDER BY id""", (asin,)).fetchall()
        alerts = c.execute("""SELECT created_at, message, severity, is_read
                              FROM alerts WHERE asin=? ORDER BY id DESC LIMIT 50""",
                           (asin,)).fetchall()
    return JSONResponse({"asin": asin, "snapshots": [dict(x) for x in snaps],
                         "alerts": [dict(x) for x in alerts]})

@app.post("/api/links/{asin}")
def api_add_link(asin: str):
    with db.get_conn() as c:
        c.execute("INSERT OR IGNORE INTO monitor_links(asin) VALUES(?)", (asin.upper(),))
    return JSONResponse({"ok": True, "asin": asin.upper()})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
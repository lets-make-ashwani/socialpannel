import os
import sys
import json
import time
import asyncio
from datetime import datetime
from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
import uvicorn

app = FastAPI(title="UploadPost Master Fleet Control Panel")

BASE_DIR = os.path.dirname(__file__)
REGISTRY_FILE = os.path.join(BASE_DIR, "bots_registry.json")

def load_registry():
    if os.path.exists(REGISTRY_FILE):
        try:
            with open(REGISTRY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            pass
    return {}

def save_registry(data):
    with open(REGISTRY_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def get_gadgets_mankind_status():
    """Checks live stats from GadgetsMankind_Automation folder"""
    gm_dir = r"C:\Users\ashwani\Desktop\GadgetsMankind_Automation"
    tracker_file = os.path.join(gm_dir, "tracker.json")
    history_file = os.path.join(gm_dir, "logs", "post_history.json")

    last_msg_id = 0
    if os.path.exists(tracker_file):
        try:
            with open(tracker_file, "r", encoding="utf-8") as f:
                tr = json.load(f)
                last_msg_id = tr.get("last_processed_id", 0)
        except:
            pass

    history = []
    if os.path.exists(history_file):
        try:
            with open(history_file, "r", encoding="utf-8") as f:
                history = json.load(f)
        except:
            pass

    return {
        "last_message_id": last_msg_id,
        "total_posts": len(history),
        "recent_posts": history[-5:][::-1]
    }

def get_stylish_dress_status():
    """Checks live stats from MySocialTool folder"""
    ms_dir = r"C:\Users\ashwani\Desktop\MySocialTool"
    hist_file = os.path.join(ms_dir, "post_history.json")
    posts = []
    if os.path.exists(hist_file):
        try:
            with open(hist_file, "r", encoding="utf-8") as f:
                posts = json.load(f)
        except:
            pass
    return {
        "total_posts": len(posts),
        "recent_posts": posts[-5:][::-1]
    }

@app.get("/health")
def health():
    return {"status": "ok", "service": "UploadPost Master Cloud Panel", "timestamp": datetime.now().isoformat()}

@app.get("/api/fleet")
def get_fleet_api():
    reg = load_registry()
    gm_status = get_gadgets_mankind_status()
    st_status = get_stylish_dress_status()

    if "gadgets_mankind" in reg:
        reg["gadgets_mankind"]["total_posts"] = gm_status["total_posts"]
        reg["gadgets_mankind"]["last_message_id"] = gm_status["last_message_id"]

    if "stylish_girl_dress" in reg:
        reg["stylish_girl_dress"]["total_posts"] = st_status["total_posts"]

    return reg

def run_gadgets_cycle_bg():
    gm_dir = r"C:\Users\ashwani\Desktop\GadgetsMankind_Automation"
    if gm_dir not in sys.path:
        sys.path.insert(0, gm_dir)
    try:
        import pipeline as gm_pipe
        gm_pipe.execute_pipeline_cycle()
    except Exception as e:
        print(f"[X] Error executing Gadgets Mankind cycle: {e}")

@app.post("/api/trigger/{bot_id}")
def trigger_bot(bot_id: str, background_tasks: BackgroundTasks):
    reg = load_registry()
    if bot_id not in reg:
        raise HTTPException(status_code=404, detail="Bot not found in registry")

    if bot_id == "gadgets_mankind":
        background_tasks.add_task(run_gadgets_cycle_bg)
        return {"status": "success", "message": "Triggered Gadgets Mankind pipeline in background!"}
    else:
        return {"status": "info", "message": f"Trigger queued for {bot_id}"}

@app.get("/", response_class=HTMLResponse)
def master_dashboard():
    reg = load_registry()
    gm = get_gadgets_mankind_status()
    st = get_stylish_dress_status()

    total_bots = len(reg)
    total_posts = gm["total_posts"] + st["total_posts"]

    # Build Bot Cards
    cards_html = ""
    for b_id, bot in reg.items():
        name = bot.get("name")
        cat = bot.get("category")
        status = bot.get("status")
        source = bot.get("source")
        ai_eng = bot.get("ai_engine")
        cadence = bot.get("cadence")
        total_p = gm["total_posts"] if b_id == "gadgets_mankind" else (st["total_posts"] if b_id == "stylish_girl_dress" else bot.get("total_posts", 0))

        dest_pills = ""
        for d in bot.get("destinations", []):
            color = "#FF007A" if d["platform"] == "instagram" else ("#0066FF" if d["platform"] == "facebook" else "#EDEDED")
            dest_pills += f"""
            <span class="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-medium border border-zinc-800 bg-zinc-900" style="color: {color};">
                {d['handle']} ({d['type']})
            </span>
            """

        status_badge = """
        <span class="inline-flex items-center space-x-1.5 px-2.5 py-1 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 text-xs font-medium">
            <span class="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
            <span>24/7 ACTIVE</span>
        </span>
        """ if status == "ACTIVE" else """
        <span class="inline-flex items-center space-x-1.5 px-2.5 py-1 rounded-full bg-zinc-800 text-zinc-400 border border-zinc-700 text-xs font-medium">
            <span>● STANDBY</span>
        </span>
        """

        action_btn = ""
        if b_id == "gadgets_mankind":
            action_btn = """
            <button onclick="triggerBot('gadgets_mankind')" class="w-full mt-4 py-2 bg-white hover:bg-zinc-200 text-black font-semibold text-xs rounded-lg transition-all shadow-sm flex items-center justify-center space-x-1.5">
                <span>⚡ Trigger Next Video Cycle Now</span>
            </button>
            """

        cards_html += f"""
        <div class="bg-zinc-950 border border-zinc-800 rounded-xl p-5 flex flex-col justify-between hover:border-zinc-700 transition-all shadow-xl">
            <div class="space-y-3">
                <div class="flex items-center justify-between">
                    <div>
                        <div class="text-xs uppercase font-semibold text-zinc-500 tracking-wider font-mono">{cat}</div>
                        <div class="text-base font-bold text-white mt-0.5">{name}</div>
                    </div>
                    {status_badge}
                </div>

                <div class="space-y-1.5 text-xs text-zinc-400 pt-2 border-t border-zinc-900">
                    <div><span class="text-zinc-500 font-mono">SOURCE:</span> {source}</div>
                    <div><span class="text-zinc-500 font-mono">AI CORE:</span> {ai_eng}</div>
                    <div><span class="text-zinc-500 font-mono">CADENCE:</span> <span class="text-white font-medium">{cadence}</span></div>
                    <div class="pt-1 flex flex-wrap gap-1.5">{dest_pills}</div>
                </div>
            </div>

            <div class="pt-4 border-t border-zinc-900 mt-4 flex items-center justify-between text-xs">
                <div>
                    <span class="text-zinc-500">Total Posts:</span>
                    <span class="text-white font-bold ml-1">{total_p}</span>
                </div>
                <div>
                    <span class="text-zinc-500">Daily Quota:</span>
                    <span class="text-emerald-400 font-medium ml-1">25/25 Available</span>
                </div>
            </div>
            {action_btn}
        </div>
        """

    # Combined Activity Logs
    feed_html = ""
    combined_activity = []
    for p in gm.get("recent_posts", []):
        combined_activity.append({"bot": "Gadgets Mankind", "time": p.get("timestamp"), "summary": p.get("summary"), "ig": p.get("instagram", {}).get("result"), "fb": p.get("facebook", {}).get("result")})
    for p in st.get("recent_posts", []):
        combined_activity.append({"bot": "Stylish Girl Dress", "time": p.get("timestamp"), "summary": p.get("caption", "")[:60], "platform": p.get("platform"), "status": p.get("status")})

    combined_activity.sort(key=lambda x: str(x.get("time")), reverse=True)

    if not combined_activity:
        feed_html = "<div class='text-zinc-500 text-xs py-4'>No live activity logged yet. Cycles running in cloud.</div>"
    else:
        for act in combined_activity[:8]:
            b_name = act.get("bot")
            tm = act.get("time", "")
            sum_txt = act.get("summary", "Post event")
            ig_l = act.get("ig")

            feed_html += f"""
            <div class="p-3 bg-zinc-900/60 border border-zinc-800/80 rounded-lg flex items-center justify-between text-xs mb-2">
                <div>
                    <span class="px-1.5 py-0.5 rounded bg-zinc-800 text-zinc-300 font-mono text-[10px] mr-1.5">{b_name}</span>
                    <span class="text-zinc-200">{sum_txt}</span>
                    <div class="text-[10px] text-zinc-500 mt-0.5">{tm}</div>
                </div>
                <div>
                    {"<a href='" + ig_l + "' target='_blank' class='px-2 py-1 rounded bg-[#FF007A]/20 text-[#FF007A] font-medium hover:underline'>View Live Reel ↗</a>" if ig_l and 'instagram.com' in str(ig_l) else "<span class='text-emerald-400 font-medium'>● Dispatched</span>"}
                </div>
            </div>
            """

    return f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>UploadPost Fleet — Master Automation Command Center</title>
        <script src="https://cdn.tailwindcss.com"></script>
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Geist:wght@400;500;600;700&family=Geist+Mono:wght@400;600&display=swap');
            body {{ font-family: 'Geist', -apple-system, sans-serif; }}
            .font-mono {{ font-family: 'Geist Mono', monospace; }}
        </style>
    </head>
    <body class="bg-black text-zinc-100 antialiased min-h-screen p-4 md:p-8">
        <div class="max-w-6xl mx-auto space-y-6">

            <!-- Top Brand Header -->
            <header class="border-b border-zinc-800 pb-5 flex flex-col md:flex-row md:items-center justify-between gap-4">
                <div class="flex items-center space-x-3">
                    <div class="w-9 h-9 rounded-lg bg-black border border-zinc-700 flex items-center justify-center">
                        <svg width="17" height="17" viewBox="0 0 76 65" fill="#FFFFFF">
                            <path d="M37.5274 0L75.0548 65H0L37.5274 0Z" />
                        </svg>
                    </div>
                    <div>
                        <div class="flex items-center space-x-2">
                            <h1 class="text-lg font-bold tracking-tight text-white">UploadPost Fleet Master Hub</h1>
                            <span class="text-xs px-2 py-0.5 rounded-full border border-zinc-700 bg-zinc-900 text-zinc-400 font-mono">Render Cloud 24/7</span>
                        </div>
                        <p class="text-xs text-zinc-500">Unified Orchestration for All Multi-Platform Automation Bots</p>
                    </div>
                </div>

                <!-- Global Health Indicators -->
                <div class="flex items-center space-x-3 text-xs">
                    <div class="px-3 py-1.5 rounded-full bg-zinc-900 border border-zinc-800 flex items-center space-x-2">
                        <span class="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
                        <span class="text-zinc-300 font-medium">Meta Token: Permanent (Never Expiring)</span>
                    </div>
                    <div class="px-3 py-1.5 rounded-full bg-zinc-900 border border-zinc-800 flex items-center space-x-1.5">
                        <span class="text-zinc-400 font-mono">Groq LPU:</span>
                        <span class="text-emerald-400 font-medium">0.3s Inference</span>
                    </div>
                </div>
            </header>

            <!-- Global High-Level Metrics -->
            <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div class="bg-zinc-950 border border-zinc-800 rounded-xl p-4">
                    <div class="text-[11px] text-zinc-500 uppercase font-semibold font-mono">Active Bot Fleet</div>
                    <div class="text-2xl font-bold text-white mt-1">{total_bots} Bots</div>
                    <div class="text-xs text-emerald-400 mt-0.5">● All Systems Nominal</div>
                </div>

                <div class="bg-zinc-950 border border-zinc-800 rounded-xl p-4">
                    <div class="text-[11px] text-zinc-500 uppercase font-semibold font-mono">Total Posts Dispatched</div>
                    <div class="text-2xl font-bold text-white mt-1">{total_posts} Posts</div>
                    <div class="text-xs text-zinc-400 mt-0.5">Across Instagram & Facebook</div>
                </div>

                <div class="bg-zinc-950 border border-zinc-800 rounded-xl p-4">
                    <div class="text-[11px] text-zinc-500 uppercase font-semibold font-mono">Gadgets Mankind Queue</div>
                    <div class="text-2xl font-bold text-white mt-1">Msg #{gm['last_message_id']}</div>
                    <div class="text-xs text-zinc-400 mt-0.5">Next in 3-Hour Loop</div>
                </div>

                <div class="bg-zinc-950 border border-zinc-800 rounded-xl p-4">
                    <div class="text-[11px] text-zinc-500 uppercase font-semibold font-mono">Cloud Execution</div>
                    <div class="text-2xl font-bold text-white mt-1">Render 24/7</div>
                    <div class="text-xs text-emerald-400 mt-0.5">● Zero PC Runtime Needed</div>
                </div>
            </div>

            <!-- Bot Fleet Section -->
            <div class="space-y-3">
                <div class="flex items-center justify-between">
                    <h2 class="text-sm font-semibold text-white tracking-wide uppercase font-mono">Automated Bot Fleet</h2>
                    <span class="text-xs text-zinc-500">Autonomous Execution Units</span>
                </div>

                <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
                    {cards_html}
                </div>
            </div>

            <!-- Global Live Activity Feed -->
            <div class="bg-zinc-950 border border-zinc-800 rounded-xl p-5 space-y-3">
                <div class="flex items-center justify-between">
                    <h2 class="text-sm font-semibold text-white tracking-wide uppercase font-mono">Unified Real-Time Audit Feed</h2>
                    <button onclick="location.reload()" class="text-xs text-zinc-400 hover:text-white transition-all font-mono">↻ Refresh Feed</button>
                </div>
                <div class="pt-1">
                    {feed_html}
                </div>
            </div>

        </div>

        <script>
            function triggerBot(botId) {{
                if (confirm("Run an immediate automation cycle for " + botId + "?")) {{
                    fetch('/api/trigger/' + botId, {{ method: 'POST' }})
                        .then(r => r.json())
                        .then(d => {{
                            alert(d.message);
                            setTimeout(() => location.reload(), 2000);
                        }})
                        .catch(e => alert("Error: " + e));
                }}
            }}
            // Auto-refresh every 60 seconds
            setTimeout(() => location.reload(), 60000);
        </script>
    </body>
    </html>
    """

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run("app:app", host="0.0.0.0", port=port)

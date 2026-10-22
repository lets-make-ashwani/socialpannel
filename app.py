import os
import sys
import json
import re
import requests
from datetime import datetime
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
import uvicorn

# UTF-8 encoding
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

app = FastAPI(title="UploadPost Master Fleet Control Panel")

GADGETS_BOT_URL = os.environ.get("GADGETS_BOT_URL", "https://gadgetsmankindautobot.onrender.com")
MONGODB_URI = os.environ.get("MONGODB_URI", os.environ.get("MONGO_URI", "")).strip()

_mongo_db = None

def get_mongo_db():
    global _mongo_db
    if not MONGODB_URI:
        return None
    if _mongo_db is not None:
        return _mongo_db
    try:
        from pymongo import MongoClient
        client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=3000)
        db_name = os.environ.get("MONGODB_DATABASE", "gadgets_mankind")
        _mongo_db = client[db_name]
        return _mongo_db
    except Exception as e:
        print(f"[!] MongoDB Atlas connection note: {e}")
        return None

def get_live_gadgets_bot_data():
    """
    Connects to gadgetsmankindautobot.onrender.com or MongoDB Atlas
    to fetch real-time state, health, countdown, and post links.
    """
    data = {
        "is_online": False,
        "status": "OFFLINE",
        "is_paused": False,
        "last_message_id": 0,
        "last_run": None,
        "next_run": None,
        "next_run_iso": None,
        "amazon_tag": "tech6s-21",
        "autodm_sent_count": 0,
        "mongodb_connected": False,
        "total_posts": 0,
        "recent_posts": []
    }

    # 1. First attempt: Query live Render endpoint
    try:
        r_health = requests.get(f"{GADGETS_BOT_URL}/health", timeout=6)
        if r_health.status_code == 200:
            h = r_health.json()
            data["is_online"] = True
            data["status"] = h.get("status", "RUNNING")
            data["is_paused"] = h.get("is_paused", False)
            data["last_run"] = h.get("last_run")
            data["next_run"] = h.get("next_run")
            data["next_run_iso"] = h.get("next_run_iso")
            data["last_message_id"] = h.get("last_message_id", 0)
            data["amazon_tag"] = h.get("amazon_tag", "tech6s-21")
            data["autodm_sent_count"] = h.get("autodm_sent_count", 0)
            data["mongodb_connected"] = h.get("mongodb_connected", False)
            data["total_posts"] = h.get("total_posts", 0)
            data["recent_posts"] = h.get("recent_posts", [])
            return data
    except Exception as e:
        print(f"[!] Live health query note: {e}")

    # 2. Second attempt: Check MongoDB Atlas directly if configured
    db = get_mongo_db()
    if db is not None:
        try:
            tracker_doc = db["automation_state"].find_one({"_id": "global_tracker"})
            if tracker_doc:
                data["is_online"] = True
                data["mongodb_connected"] = True
                data["last_message_id"] = tracker_doc.get("last_processed_id", 0)
            
            posts = list(db["post_history"].find({}, {"_id": 0}).sort("timestamp", -1).limit(10))
            if posts:
                data["is_online"] = True
                data["total_posts"] = len(posts)
                data["recent_posts"] = posts
                data["last_run"] = posts[0].get("timestamp")

            data["autodm_sent_count"] = db["autodm_replies"].count_documents({})
        except Exception as e:
            print(f"[!] MongoDB direct query note: {e}")

    return data

@app.get("/health")
def health():
    return {"status": "ok", "service": "UploadPost Master Cloud Panel", "timestamp": datetime.now().isoformat()}

@app.get("/api/gadgets/status")
def proxy_status():
    return get_live_gadgets_bot_data()

@app.get("/api/gadgets/logs")
def proxy_logs():
    try:
        r = requests.get(f"{GADGETS_BOT_URL}/api/logs?limit=80", timeout=5)
        return r.json()
    except Exception as e:
        return {"logs": [f"[Connecting] Fetching logs from {GADGETS_BOT_URL}..."]}

@app.post("/api/gadgets/pause")
def proxy_pause():
    try:
        r = requests.post(f"{GADGETS_BOT_URL}/pause", timeout=10)
        return r.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/gadgets/resume")
def proxy_resume():
    try:
        r = requests.post(f"{GADGETS_BOT_URL}/resume", timeout=10)
        return r.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/gadgets/trigger")
def proxy_trigger():
    try:
        r = requests.post(f"{GADGETS_BOT_URL}/trigger-now", timeout=10)
        return r.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

BESTFIND_BOT_URL = os.environ.get("BESTFIND_BOT_URL", "https://bestfindautobot.onrender.com")

@app.post("/api/bestfind/trigger")
def proxy_bestfind_trigger():
    try:
        r = requests.post(f"{BESTFIND_BOT_URL}/trigger-now", timeout=10)
        return r.json()
    except Exception as e:
        return {"status": "error", "message": f"Best Find Bot notice: {e}"}

@app.get("/", response_class=HTMLResponse)
def master_dashboard():
    gm = get_live_gadgets_bot_data()
    is_paused = gm.get("is_paused", False)
    last_msg_id = gm.get("last_message_id", 0)
    total_posts = gm.get("total_posts", 0)
    next_run = gm.get("next_run") or "In 3 hours"
    amazon_tag = gm.get("amazon_tag", "tech6s-21")
    autodm_count = gm.get("autodm_sent_count", 0)
    mongo_ok = gm.get("mongodb_connected", False)

    # Status Badge
    if not gm["is_online"]:
        status_badge = """
        <span class="inline-flex items-center space-x-1.5 px-2.5 py-1 rounded-full bg-red-500/10 text-red-400 border border-red-500/20 text-xs font-medium">
            <span class="w-1.5 h-1.5 rounded-full bg-red-400"></span>
            <span>CONNECTING...</span>
        </span>
        """
    elif is_paused:
        status_badge = """
        <span class="inline-flex items-center space-x-1.5 px-2.5 py-1 rounded-full bg-amber-500/10 text-amber-400 border border-amber-500/20 text-xs font-medium">
            <span class="w-1.5 h-1.5 rounded-full bg-amber-400"></span>
            <span>PAUSED</span>
        </span>
        """
    else:
        status_badge = """
        <span class="inline-flex items-center space-x-1.5 px-2.5 py-1 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 text-xs font-medium">
            <span class="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
            <span>24/7 ACTIVE</span>
        </span>
        """

    # Start / Stop Toggle Button
    if is_paused:
        toggle_button = """
        <button onclick="controlBot('resume')" class="px-3.5 py-2 bg-emerald-500 hover:bg-emerald-400 text-black font-semibold text-xs rounded-lg transition-all shadow-sm flex items-center space-x-1.5">
            <span>▶️ Resume Bot</span>
        </button>
        """
    else:
        toggle_button = """
        <button onclick="controlBot('pause')" class="px-3.5 py-2 bg-red-500 hover:bg-red-400 text-white font-semibold text-xs rounded-lg transition-all shadow-sm flex items-center space-x-1.5">
            <span>⏸️ Pause Bot</span>
        </button>
        """

    # Recent activity logs from live bot
    feed_html = ""
    recent_list = gm.get("recent_posts", [])
    if not recent_list:
        feed_html = """
        <div class="text-zinc-500 text-xs py-4 flex items-center space-x-2">
            <span class="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
            <span>Bot is active in cloud. Waiting for next 3-hour scheduled post or click 'Trigger Next Video'.</span>
        </div>
        """
    else:
        for p in recent_list:
            m_id = p.get("message_id") or p.get("telegram_message_id", "28824")
            summary = p.get("product_name") or p.get("summary", "Trending home tech gadget")
            ig_url = p.get("instagram_link") or (p.get("instagram", {}).get("result") if isinstance(p.get("instagram"), dict) else None)
            amz_url = p.get("amazon_link", f"https://www.amazon.in/s?k=gadgets&tag={amazon_tag}")
            
            feed_html += f"""
            <div class="p-3.5 bg-zinc-900/60 border border-zinc-800/80 rounded-lg flex flex-col sm:flex-row sm:items-center justify-between text-xs mb-2 gap-2">
                <div>
                    <span class="px-2 py-0.5 rounded bg-zinc-800 text-white font-mono text-[11px] mr-2">Msg #{m_id}</span>
                    <span class="text-zinc-200">{summary}</span>
                </div>
                <div class="flex items-center space-x-2 flex-wrap gap-1">
                    <a href="{amz_url}" target="_blank" class="px-2.5 py-1 rounded bg-[#FF9900]/20 text-[#FF9900] font-semibold hover:underline flex items-center gap-1">
                        🛒 Amazon ({amazon_tag})
                    </a>
                    {"<a href='" + str(ig_url) + "' target='_blank' class='px-2.5 py-1 rounded bg-[#FF007A]/20 text-[#FF007A] font-semibold hover:underline flex items-center space-x-1'><span>Instagram Reel</span> <span>↗</span></a>" if ig_url and 'instagram.com' in str(ig_url) else "<span class='text-emerald-400 font-medium'>● Published to Meta</span>"}
                </div>
            </div>
            """

    return f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>UploadPost Fleet — Master Automation Control Panel</title>
        <script src="https://cdn.tailwindcss.com"></script>
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Geist:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');
            body {{ font-family: 'Geist', -apple-system, sans-serif; }}
            .terminal-font {{ font-family: 'JetBrains Mono', monospace; }}
            ::-webkit-scrollbar {{ width: 6px; height: 6px; }}
            ::-webkit-scrollbar-track {{ background: #09090b; }}
            ::-webkit-scrollbar-thumb {{ background: #27272a; border-radius: 3px; }}
        </style>
    </head>
    <body class="bg-black text-zinc-100 antialiased min-h-screen p-4 md:p-8">
        <div class="max-w-5xl mx-auto space-y-6">

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
                        <p class="text-xs text-zinc-500">Fleet Control Center &bull; Live Telemetry &bull; Auto-DM & Amazon Associates</p>
                    </div>
                </div>

                <!-- Global Health Indicators -->
                <div class="flex items-center space-x-3 text-xs">
                    <span class="px-2.5 py-1 rounded-full text-[11px] font-medium {'bg-emerald-950 text-emerald-400 border border-emerald-800' if mongo_ok else 'bg-zinc-900 text-zinc-400 border border-zinc-800'} flex items-center gap-1">
                        <span class="w-1.5 h-1.5 rounded-full {'bg-emerald-400' if mongo_ok else 'bg-zinc-500'}"></span>
                        {'MongoDB Atlas Sync' if mongo_ok else 'Telegram Cloud Sync'}
                    </span>
                    <a href="{GADGETS_BOT_URL}" target="_blank" class="px-3 py-1.5 rounded-full bg-zinc-900 border border-zinc-800 text-zinc-400 hover:text-white transition-all flex items-center space-x-1">
                        <span>Direct URL</span>
                        <span>↗</span>
                    </a>
                </div>
            </header>

            <!-- Global High-Level Metrics -->
            <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div class="bg-zinc-950 border border-zinc-800 rounded-xl p-4">
                    <div class="text-[11px] text-zinc-500 uppercase font-semibold font-mono">Active Bot Fleet</div>
                    <div class="text-2xl font-bold text-white mt-1">2 Bots Live</div>
                    <div class="text-xs text-emerald-400 mt-0.5">● Gadgets Mankind + Best Find</div>
                </div>

                <div class="bg-zinc-950 border border-zinc-800 rounded-xl p-4">
                    <div class="text-[11px] text-zinc-500 uppercase font-semibold font-mono">Amazon Associate Tag</div>
                    <div class="text-2xl font-bold text-[#FF9900] mt-1">{amazon_tag}</div>
                    <div class="text-xs text-zinc-400 mt-0.5">Amazon.in High Converting</div>
                </div>

                <div class="bg-zinc-950 border border-zinc-800 rounded-xl p-4">
                    <div class="text-[11px] text-zinc-500 uppercase font-semibold font-mono">Auto-DMs Delivered</div>
                    <div class="text-2xl font-bold text-pink-500 mt-1">{autodm_count}</div>
                    <div class="text-xs text-zinc-400 mt-0.5">Comment-to-DM Active</div>
                </div>

                <div class="bg-zinc-950 border border-zinc-800 rounded-xl p-4">
                    <div class="text-[11px] text-zinc-500 uppercase font-semibold font-mono">Queue Progress</div>
                    <div class="text-2xl font-bold text-white mt-1">Msg #{last_msg_id}</div>
                    <div class="text-xs text-emerald-400 mt-0.5">● Auto-incrementing</div>
                </div>
            </div>

            <!-- Bot Fleet Section -->
            <div class="space-y-3">
                <div class="flex items-center justify-between">
                    <h2 class="text-sm font-semibold text-white tracking-wide uppercase font-mono">Autonomous Execution Units</h2>
                    <span class="text-xs text-zinc-500">Live Cadence: Every 3 Hours</span>
                </div>

                <div class="grid grid-cols-1 md:grid-cols-2 gap-5">

                    <!-- CARD 1: GADGETS MANKIND AUTO-DUBBER WITH LIVE COUNTDOWN -->
                    <div class="bg-zinc-950 border border-zinc-800 rounded-xl p-5 flex flex-col justify-between hover:border-zinc-700 transition-all shadow-xl">
                        <div class="space-y-4">
                            <div class="flex items-center justify-between">
                                <div>
                                    <div class="text-xs uppercase font-semibold text-zinc-500 tracking-wider font-mono">Tech & Home Gadgets</div>
                                    <div class="text-base font-bold text-white mt-0.5">Gadgets Mankind Auto-Dubber</div>
                                </div>
                                {status_badge}
                            </div>

                            <!-- COUNTDOWN BANNER -->
                            <div class="p-3.5 bg-gradient-to-r from-zinc-900 to-zinc-900/40 border border-zinc-800 rounded-lg">
                                <div class="text-[11px] text-zinc-400 uppercase font-semibold tracking-wider font-mono flex items-center justify-between">
                                    <span>Next Scheduled Reel In:</span>
                                    <span class="w-2 h-2 rounded-full bg-indigo-500 animate-ping"></span>
                                </div>
                                <div id="panel-countdown" class="text-2xl font-bold font-mono text-indigo-400 mt-1">--:--:--</div>
                                <div class="text-[11px] text-zinc-500 mt-0.5">Cadence: 8 Reels / 24 Hours &bull; Oldest ➔ Newest</div>
                            </div>

                            <div class="space-y-2 text-xs text-zinc-300 pt-2 border-t border-zinc-900">
                                <div><span class="text-zinc-500 font-mono">SOURCE:</span> Telegram @allterapost</div>
                                <div><span class="text-zinc-500 font-mono">AI ENGINE:</span> Groq Whisper + Edge-TTS Neural Voice</div>
                                <div><span class="text-zinc-500 font-mono">MONETIZATION:</span> Amazon.in ({amazon_tag}) + Native Auto-DM</div>
                                <div class="pt-1 flex flex-wrap gap-1.5">
                                    <span class="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-medium border border-[#FF007A]/30 bg-[#FF007A]/10 text-[#FF007A]">
                                        @gadgetsmankind (Reels)
                                    </span>
                                    <span class="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-medium border border-[#0066FF]/30 bg-[#0066FF]/10 text-[#0066FF]">
                                        Gadgets mankind (Facebook)
                                    </span>
                                </div>
                            </div>
                        </div>

                        <!-- Bot Action Controls: Start/Stop + Trigger -->
                        <div class="pt-4 border-t border-zinc-900 mt-4 space-y-2.5">
                            <div class="flex items-center space-x-2">
                                {toggle_button}
                                <button onclick="triggerNextNow()" class="flex-1 py-2 bg-white hover:bg-zinc-200 text-black font-semibold text-xs rounded-lg transition-all shadow-sm flex items-center justify-center space-x-1">
                                    <span>⚡ Trigger Next Video Now</span>
                                </button>
                            </div>
                        </div>
                    </div>

                    <!-- CARD 2: BEST FIND AUTONOMOUS PUBLISHER -->
                    <div class="bg-zinc-950 border border-zinc-800 rounded-xl p-5 flex flex-col justify-between hover:border-zinc-700 transition-all shadow-xl">
                        <div class="space-y-4">
                            <div class="flex items-center justify-between">
                                <div>
                                    <div class="text-xs uppercase font-semibold text-amber-500 tracking-wider font-mono">Useful Products & Reviews</div>
                                    <div class="text-base font-bold text-white mt-0.5">Best Find Autonomous Publisher</div>
                                </div>
                                <div class="flex items-center space-x-2">
                                    <span class="w-2.5 h-2.5 rounded-full bg-amber-400 animate-pulse"></span>
                                    <span class="text-xs text-amber-400 font-semibold">7-Day Optimizer</span>
                                </div>
                            </div>

                            <!-- EXPERIMENT CADENCE BANNER -->
                            <div class="p-3.5 bg-gradient-to-r from-zinc-900 to-zinc-900/40 border border-zinc-800 rounded-lg">
                                <div class="text-[11px] text-zinc-400 uppercase font-semibold tracking-wider font-mono flex items-center justify-between">
                                    <span>Cadence Experiment Slots:</span>
                                    <span class="text-amber-400 font-bold">4 Daily Slots</span>
                                </div>
                                <div class="text-sm font-bold font-mono text-amber-300 mt-1">09:30 &bull; 14:00 &bull; 18:30 &bull; 21:30 IST</div>
                                <div class="text-[11px] text-zinc-500 mt-0.5">Analyzes 7-day engagement & locks winning timeframe</div>
                            </div>

                            <div class="space-y-2 text-xs text-zinc-300 pt-2 border-t border-zinc-900">
                                <div><span class="text-zinc-500 font-mono">SOURCE:</span> Telegram @allterapost</div>
                                <div><span class="text-zinc-500 font-mono">LANGUAGE:</span> Original Audio Preserved (No Translation)</div>
                                <div><span class="text-zinc-500 font-mono">MONETIZATION:</span> Line 1 Amazon Buy Link ({amazon_tag})</div>
                                <div class="pt-1 flex flex-wrap gap-1.5">
                                    <span class="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-medium border border-[#0066FF]/30 bg-[#0066FF]/10 text-[#0066FF]">
                                        Facebook Page: best find (ID: 255894584272909)
                                    </span>
                                </div>
                            </div>
                        </div>

                        <!-- Bot Action Controls: Trigger + Panel Link -->
                        <div class="pt-4 border-t border-zinc-900 mt-4 space-y-2.5">
                            <div class="flex items-center space-x-2">
                                <button onclick="triggerBestFindNow()" class="flex-1 py-2 bg-gradient-to-r from-amber-500 to-amber-600 hover:from-amber-400 hover:to-amber-500 text-zinc-950 font-bold text-xs rounded-lg transition-all shadow-sm flex items-center justify-center space-x-1">
                                    <span>⚡ Trigger Best Find Video</span>
                                </button>
                                <a href="https://bestfindautobot.onrender.com" target="_blank" class="px-3 py-2 bg-zinc-900 hover:bg-zinc-800 text-zinc-300 font-semibold text-xs rounded-lg border border-zinc-800 flex items-center space-x-1">
                                    <span>Bot Panel ↗</span>
                                </a>
                            </div>
                        </div>
                    </div>

                </div>
            </div>

            <!-- LIVE TERMINAL CONSOLE VIEWER -->
            <div class="bg-zinc-950 border border-zinc-800 rounded-xl overflow-hidden shadow-2xl">
                <div class="bg-zinc-900/90 px-4 py-2.5 border-b border-zinc-800 flex items-center justify-between">
                    <div class="flex items-center space-x-2">
                        <span class="w-3 h-3 rounded-full bg-red-500/80 inline-block"></span>
                        <span class="w-3 h-3 rounded-full bg-amber-500/80 inline-block"></span>
                        <span class="w-3 h-3 rounded-full bg-emerald-500/80 inline-block"></span>
                        <span class="text-xs text-zinc-400 font-medium ml-2 terminal-font">bash — fleet-live-telemetry.log</span>
                    </div>
                    <div class="flex items-center space-x-2 text-[11px] text-zinc-500">
                        <span class="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
                        <span>Streamed via gadgetsmankindautobot</span>
                    </div>
                </div>
                <div id="master-terminal" class="p-4 terminal-font text-xs text-emerald-400 bg-black/90 h-56 overflow-y-auto space-y-1">
                    <div class="text-zinc-500">[System] Connecting to live fleet terminal...</div>
                </div>
            </div>

            <!-- Global Live Activity Feed -->
            <div class="bg-zinc-950 border border-zinc-800 rounded-xl p-5 space-y-3">
                <div class="flex items-center justify-between">
                    <div class="flex items-center space-x-2">
                        <span class="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
                        <h2 class="text-sm font-semibold text-white tracking-wide uppercase font-mono">Live Publishing Audit Stream</h2>
                    </div>
                    <button onclick="location.reload()" class="text-xs text-zinc-400 hover:text-white transition-all font-mono">↻ Refresh Feed</button>
                </div>
                <div class="pt-1">
                    {feed_html}
                </div>
            </div>

        </div>

        <script>
            // Live Countdown for Fleet Card
            const nextRunStr = "{gm.get('next_run', '')}";
            const nextRunTarget = nextRunStr ? new Date(nextRunStr).getTime() : 0;
            const isPaused = {'true' if is_paused else 'false'};

            function updatePanelCountdown() {{
                const el = document.getElementById('panel-countdown');
                if (!el) return;

                if (isPaused) {{
                    el.innerText = "PAUSED";
                    return;
                }}
                if (!nextRunTarget || isNaN(nextRunTarget)) {{
                    el.innerText = "Every 3 Hours";
                    return;
                }}

                const now = new Date().getTime();
                const distance = nextRunTarget - now;

                if (distance <= 0) {{
                    el.innerText = "PROCESSING NOW...";
                    return;
                }}

                const hours = Math.floor(distance / (1000 * 60 * 60));
                const minutes = Math.floor((distance % (1000 * 60 * 60)) / (1000 * 60));
                const seconds = Math.floor((distance % (1000 * 60)) / 1000);

                const pad = (n) => String(n).padStart(2, '0');
                el.innerText = `${{pad(hours)}}h : ${{pad(minutes)}}m : ${{pad(seconds)}}s`;
            }}

            setInterval(updatePanelCountdown, 1000);
            updatePanelCountdown();

            // Terminal Log Poller
            function fetchMasterLogs() {{
                fetch('/api/gadgets/logs')
                    .then(r => r.json())
                    .then(data => {{
                        if (data && data.logs) {{
                            const term = document.getElementById('master-terminal');
                            const wasScrolledBottom = term.scrollHeight - term.clientHeight <= term.scrollTop + 50;

                            term.innerHTML = data.logs.map(line => {{
                                let colorClass = 'text-zinc-300';
                                if (line.includes('[+]') || line.includes('[🍃]') || line.includes('[📩]')) colorClass = 'text-emerald-400';
                                else if (line.includes('[*]') || line.includes('[🧹]') || line.includes('[🏷️]')) colorClass = 'text-cyan-400';
                                else if (line.includes('[!]')) colorClass = 'text-amber-400';
                                else if (line.includes('[X]') || line.includes('Error')) colorClass = 'text-rose-400';
                                return `<div class="${{colorClass}}">${{line}}</div>`;
                            }}).join('') + '<div class="text-zinc-600 animate-pulse">_</div>';

                            if (wasScrolledBottom) {{
                                term.scrollTop = term.scrollHeight;
                            }}
                        }}
                    }})
                    .catch(e => console.error("Master log glitch", e));
            }}

            setInterval(fetchMasterLogs, 3000);
            fetchMasterLogs();

            function triggerNextNow() {{
                if (confirm("Run an immediate cycle to fetch, dub, and publish the next video from Telegram to Instagram & Facebook?")) {{
                    fetch('/api/gadgets/trigger', {{ method: 'POST' }})
                        .then(r => r.json())
                        .then(d => {{
                            alert(d.message || "Cycle triggered in background!");
                            fetchMasterLogs();
                        }})
                        .catch(e => alert("Error triggering cycle: " + e));
                }}
            }}

            function triggerBestFindNow() {{
                if (confirm("Publish the next video to Facebook Page 'best find' right now?")) {{
                    fetch('/api/bestfind/trigger', {{ method: 'POST' }})
                        .then(r => r.json())
                        .then(d => {{
                            alert(d.message || "Best Find cycle triggered!");
                        }})
                        .catch(e => alert("Error triggering Best Find: " + e));
                }}
            }}

            function controlBot(action) {{
                const endpoint = action === 'pause' ? '/api/gadgets/pause' : '/api/gadgets/resume';
                const label = action === 'pause' ? 'STOP / PAUSE' : 'START / RESUME';
                if (confirm("Are you sure you want to " + label + " the automated 3-hour scheduler?")) {{
                    fetch(endpoint, {{ method: 'POST' }})
                        .then(r => r.json())
                        .then(d => {{
                            alert(d.message || ("Bot " + label + " successful!"));
                            setTimeout(() => location.reload(), 1500);
                        }})
                        .catch(e => alert("Error: " + e));
                }}
            }}
        </script>
    </body>
    </html>
    """

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run("app:app", host="0.0.0.0", port=port)

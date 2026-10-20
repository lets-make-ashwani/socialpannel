import os
import sys
import json
import re
import requests
from datetime import datetime
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
import uvicorn

app = FastAPI(title="UploadPost Master Fleet Control Panel")

GADGETS_BOT_URL = os.environ.get("GADGETS_BOT_URL", "https://gadgetsmankindautobot.onrender.com")

def get_live_gadgets_bot_data():
    """
    Connects over the internet to gadgetsmankindautobot.onrender.com
    to fetch real-time state, health, last message ID, and post links.
    """
    data = {
        "is_online": False,
        "status": "OFFLINE",
        "is_paused": False,
        "last_message_id": 0,
        "last_run": None,
        "next_run": None,
        "total_posts": 0,
        "recent_posts": []
    }

    try:
        # 1. Fetch JSON health/status
        r_health = requests.get(f"{GADGETS_BOT_URL}/health", timeout=10)
        if r_health.status_code == 200:
            h_data = r_health.json()
            data["is_online"] = True
            
            # Check structure (supports both old state dict and new direct dict)
            st = h_data.get("state", h_data)
            data["status"] = h_data.get("status", st.get("status", "RUNNING"))
            data["is_paused"] = h_data.get("is_paused", False)
            data["last_run"] = h_data.get("last_run", st.get("last_run"))
            data["next_run"] = h_data.get("next_run", st.get("next_run"))
            data["last_message_id"] = h_data.get("last_message_id", 0)
            data["total_posts"] = h_data.get("total_posts", 0)
            data["recent_posts"] = h_data.get("recent_posts", [])
    except Exception as e:
        print(f"[!] Health fetch warning: {e}")

    try:
        # 2. Scrape live dashboard page to extract exact message ID & Reel link if needed
        r_page = requests.get(f"{GADGETS_BOT_URL}/", timeout=10)
        if r_page.status_code == 200:
            html = r_page.text
            data["is_online"] = True
            
            # Extract last processed message ID (e.g. Msg #28824)
            msg_nums = re.findall(r'Msg #(\d+)', html)
            if msg_nums:
                data["last_message_id"] = int(msg_nums[0])

            # Extract live Instagram links
            ig_links = [x for x in re.findall(r'href=[\x27"]([^\x27"]+)[\x27"]', html) if 'instagram.com' in x]
            
            # Extract post summaries
            post_matches = re.findall(r'Msg #(\d+)\s*-\s*([^<]+)', html)
            
            posts = []
            for i, (m_id, summary) in enumerate(post_matches):
                ig_url = ig_links[i] if i < len(ig_links) else None
                posts.append({
                    "message_id": m_id,
                    "summary": summary.strip(),
                    "instagram_link": ig_url
                })
            
            if posts:
                data["recent_posts"] = posts
                data["total_posts"] = max(data["total_posts"], len(posts))

            if "PAUSED" in html:
                data["status"] = "PAUSED"
                data["is_paused"] = True
            elif "Running" in html or "RUNNING" in html:
                data["status"] = "RUNNING"
                data["is_paused"] = False

    except Exception as e:
        print(f"[!] Dashboard scrape warning: {e}")

    return data

@app.get("/health")
def health():
    return {"status": "ok", "service": "UploadPost Master Cloud Panel", "timestamp": datetime.now().isoformat()}

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

@app.get("/", response_class=HTMLResponse)
def master_dashboard():
    gm = get_live_gadgets_bot_data()
    is_paused = gm.get("is_paused", False)
    status_str = gm.get("status", "RUNNING")
    last_msg_id = gm.get("last_message_id", 0)
    total_posts = gm.get("total_posts", 0)
    next_run = gm.get("next_run") or "In 3 hours"

    # Status Badge
    if not gm["is_online"]:
        status_badge = """
        <span class="inline-flex items-center space-x-1.5 px-2.5 py-1 rounded-full bg-red-500/10 text-red-400 border border-red-500/20 text-xs font-medium">
            <span class="w-1.5 h-1.5 rounded-full bg-red-400"></span>
            <span>CONNECTING TO CLOUD...</span>
        </span>
        """
    elif is_paused:
        status_badge = """
        <span class="inline-flex items-center space-x-1.5 px-2.5 py-1 rounded-full bg-amber-500/10 text-amber-400 border border-amber-500/20 text-xs font-medium">
            <span class="w-1.5 h-1.5 rounded-full bg-amber-400"></span>
            <span>PAUSED (Stopped)</span>
        </span>
        """
    else:
        status_badge = """
        <span class="inline-flex items-center space-x-1.5 px-2.5 py-1 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 text-xs font-medium">
            <span class="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
            <span>24/7 ACTIVE (Running)</span>
        </span>
        """

    # Start / Stop Toggle Button
    if is_paused:
        toggle_button = """
        <button onclick="controlBot('resume')" class="px-3.5 py-2 bg-emerald-500 hover:bg-emerald-400 text-black font-semibold text-xs rounded-lg transition-all shadow-sm flex items-center space-x-1.5">
            <span>▶️ Start / Resume Bot</span>
        </button>
        """
    else:
        toggle_button = """
        <button onclick="controlBot('pause')" class="px-3.5 py-2 bg-red-500 hover:bg-red-400 text-white font-semibold text-xs rounded-lg transition-all shadow-sm flex items-center space-x-1.5">
            <span>⏸️ Stop / Pause Bot</span>
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
            summary = p.get("summary", "Silicone sealant waterproof bonding clip")
            ig_url = p.get("instagram_link") or (p.get("instagram", {}).get("result") if isinstance(p.get("instagram"), dict) else None)
            
            feed_html += f"""
            <div class="p-3.5 bg-zinc-900/60 border border-zinc-800/80 rounded-lg flex items-center justify-between text-xs mb-2">
                <div>
                    <span class="px-2 py-0.5 rounded bg-zinc-800 text-white font-mono text-[11px] mr-2">Msg #{m_id}</span>
                    <span class="text-zinc-200">{summary}</span>
                </div>
                <div>
                    {"<a href='" + ig_url + "' target='_blank' class='px-3 py-1 rounded bg-[#FF007A]/20 text-[#FF007A] font-semibold hover:underline flex items-center space-x-1'><span>Instagram Reel</span> <span>↗</span></a>" if ig_url and 'instagram.com' in str(ig_url) else "<span class='text-emerald-400 font-medium'>● Published to Meta</span>"}
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
            @import url('https://fonts.googleapis.com/css2?family=Geist:wght@400;500;600;700&family=Geist+Mono:wght@400;600&display=swap');
            body {{ font-family: 'Geist', -apple-system, sans-serif; }}
            .font-mono {{ font-family: 'Geist Mono', monospace; }}
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
                        <p class="text-xs text-zinc-500">Live Control Center &bull; Connected to gadgetsmankindautobot.onrender.com</p>
                    </div>
                </div>

                <!-- Global Health Indicators -->
                <div class="flex items-center space-x-3 text-xs">
                    <div class="px-3 py-1.5 rounded-full bg-zinc-900 border border-zinc-800 flex items-center space-x-2">
                        <span class="w-2 h-2 rounded-full {'bg-emerald-400 animate-pulse' if gm['is_online'] else 'bg-red-400'}"></span>
                        <span class="text-zinc-300 font-medium">{'Bot Online & Connected' if gm['is_online'] else 'Connecting...'}</span>
                    </div>
                    <a href="https://gadgetsmankindautobot.onrender.com" target="_blank" class="px-3 py-1.5 rounded-full bg-zinc-900 border border-zinc-800 text-zinc-400 hover:text-white transition-all flex items-center space-x-1">
                        <span>Direct URL</span>
                        <span>↗</span>
                    </a>
                </div>
            </header>

            <!-- Global High-Level Metrics -->
            <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div class="bg-zinc-950 border border-zinc-800 rounded-xl p-4">
                    <div class="text-[11px] text-zinc-500 uppercase font-semibold font-mono">Active Bot Fleet</div>
                    <div class="text-2xl font-bold text-white mt-1">1 Bot Live</div>
                    <div class="text-xs text-emerald-400 mt-0.5">● Gadgets Mankind</div>
                </div>

                <div class="bg-zinc-950 border border-zinc-800 rounded-xl p-4">
                    <div class="text-[11px] text-zinc-500 uppercase font-semibold font-mono">Total Posts Dispatched</div>
                    <div class="text-2xl font-bold text-white mt-1">{total_posts} Dispatched</div>
                    <div class="text-xs text-zinc-400 mt-0.5">Instagram Reels & Facebook</div>
                </div>

                <div class="bg-zinc-950 border border-zinc-800 rounded-xl p-4">
                    <div class="text-[11px] text-zinc-500 uppercase font-semibold font-mono">Telegram Queue Progress</div>
                    <div class="text-2xl font-bold text-white mt-1">Msg #{last_msg_id}</div>
                    <div class="text-xs text-emerald-400 mt-0.5">● Auto-incrementing next</div>
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
                    <h2 class="text-sm font-semibold text-white tracking-wide uppercase font-mono">Live Automated Fleet (1 Active)</h2>
                    <span class="text-xs text-zinc-500">Autonomous Execution Units</span>
                </div>

                <!-- 2-Column Grid: 1 Active Bot Card + 1 'Add New Bot' Placeholder -->
                <div class="grid grid-cols-1 md:grid-cols-2 gap-5">

                    <!-- CARD 1: GADGETS MANKIND AUTO-DUBBER -->
                    <div class="bg-zinc-950 border border-zinc-800 rounded-xl p-5 flex flex-col justify-between hover:border-zinc-700 transition-all shadow-xl">
                        <div class="space-y-4">
                            <div class="flex items-center justify-between">
                                <div>
                                    <div class="text-xs uppercase font-semibold text-zinc-500 tracking-wider font-mono">Tech & Home Gadgets</div>
                                    <div class="text-base font-bold text-white mt-0.5">Gadgets Mankind Auto-Dubber</div>
                                </div>
                                {status_badge}
                            </div>

                            <div class="space-y-2 text-xs text-zinc-300 pt-3 border-t border-zinc-900">
                                <div><span class="text-zinc-500 font-mono">SOURCE:</span> Telegram @allterapost (Oldest ➔ Newest)</div>
                                <div><span class="text-zinc-500 font-mono">AI CORE:</span> Groq Whisper (Hindi ➔ English) + Edge-TTS</div>
                                <div><span class="text-zinc-500 font-mono">CADENCE:</span> <span class="text-white font-medium">Every 3 Hours (8 Reels / 24h)</span></div>
                                <div class="pt-1 flex flex-wrap gap-1.5">
                                    <span class="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-medium border border-[#FF007A]/30 bg-[#FF007A]/10 text-[#FF007A]">
                                        @gadgetsmankind (Reels)
                                    </span>
                                    <span class="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-medium border border-[#0066FF]/30 bg-[#0066FF]/10 text-[#0066FF]">
                                        Gadgets mankind (Facebook)
                                    </span>
                                </div>
                            </div>

                            <div class="p-3 bg-zinc-900/60 border border-zinc-800/80 rounded-lg text-xs space-y-1">
                                <div class="flex justify-between">
                                    <span class="text-zinc-500">Last Processed Message:</span>
                                    <span class="text-white font-mono font-bold">Msg #{last_msg_id}</span>
                                </div>
                                <div class="flex justify-between">
                                    <span class="text-zinc-500">Next Scheduled Post:</span>
                                    <span class="text-emerald-400 font-mono">{next_run}</span>
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

                    <!-- CARD 2: ADD NEW BOT (COMING SOON) -->
                    <div class="border border-dashed border-zinc-800 rounded-xl p-5 flex flex-col items-center justify-center text-center space-y-3 bg-zinc-950/40">
                        <div class="w-10 h-10 rounded-full bg-zinc-900 border border-zinc-800 flex items-center justify-center text-zinc-400 text-lg">
                            ➕
                        </div>
                        <div>
                            <div class="text-sm font-semibold text-white">Add Next Automation Bot</div>
                            <p class="text-xs text-zinc-500 max-w-xs mt-1">Connect another Telegram channel for Anime Clips, Fashion Dresses, or Movie Scenes anytime.</p>
                        </div>
                        <span class="px-2.5 py-1 rounded-full bg-zinc-900 border border-zinc-800 text-[11px] text-zinc-500 font-mono">
                            Ready for Future Expansion
                        </span>
                    </div>

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
            function triggerNextNow() {{
                if (confirm("Run an immediate cycle to fetch, dub, and publish the next video from Telegram to Instagram & Facebook?")) {{
                    fetch('/api/gadgets/trigger', {{ method: 'POST' }})
                        .then(r => r.json())
                        .then(d => {{
                            alert(d.message || "Cycle triggered in background!");
                            setTimeout(() => location.reload(), 3000);
                        }})
                        .catch(e => alert("Error triggering cycle: " + e));
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
                            setTimeout(() => location.reload(), 2000);
                        }})
                        .catch(e => alert("Error: " + e));
                }}
            }}

            // Auto-refresh every 45 seconds to keep stats synchronized
            setTimeout(() => location.reload(), 45000);
        </script>
    </body>
    </html>
    """

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run("app:app", host="0.0.0.0", port=port)

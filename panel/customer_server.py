#!/usr/bin/env python3
import http.server
import socketserver
import json
import os
import urllib.parse
import urllib.request
import subprocess
import time
import secrets

PORT = 3000
KHAREJ_API = os.environ.get("KHAREJ_API", "https://damn.donyayelenttormoz.ir:9443")
PRIMARY_DNS = os.environ.get("PRIMARY_DNS", "77.104.92.169")
DATA_DIR = "/opt/smartdns-customer"
DATA_FILE = os.path.join(DATA_DIR, "customer_data.json")

os.makedirs(DATA_DIR, exist_ok=True)

def load_customer_db():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    initial = {
        "whitelistedIps": [],
        "receipts": [],
        "subscribers": []
    }
    save_customer_db(initial)
    return initial

def save_customer_db(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)

HTML_CUSTOMER = f"""<!DOCTYPE html>
<html lang="en" class="dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SmartDNS Console Gaming Hub</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;700&display=swap" rel="stylesheet">
    <style>
        body {{ font-family: 'Plus Jakarta Sans', sans-serif; background-color: #07090e; color: #f1f5f9; }}
        .font-mono {{ font-family: 'JetBrains Mono', monospace; }}
        .glass-panel {{ background: rgba(15, 23, 42, 0.75); backdrop-filter: blur(16px); border: 1px solid rgba(255, 255, 255, 0.07); }}
        .glow-emerald {{ box-shadow: 0 0 25px -5px rgba(16, 185, 129, 0.25); }}
        .glow-blue {{ box-shadow: 0 0 25px -5px rgba(59, 130, 246, 0.25); }}
        .glow-indigo {{ box-shadow: 0 0 25px -5px rgba(99, 102, 241, 0.25); }}
    </style>
</head>
<body class="min-h-screen antialiased selection:bg-indigo-500 selection:text-white flex flex-col">

    <!-- Toast Notification Container -->
    <div id="toastContainer" class="fixed top-5 right-5 z-50 flex flex-col gap-2 pointer-events-none"></div>

    <div class="max-w-5xl mx-auto w-full p-6 md:p-8 space-y-8 flex-1">
        
        <!-- Header -->
        <header class="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-6 border-b border-gray-800">
            <div class="flex items-center gap-3">
                <div class="p-2.5 rounded-2xl bg-indigo-500/10 border border-indigo-500/20 text-indigo-400">
                    <svg class="w-7 h-7" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"/>
                    </svg>
                </div>
                <div>
                    <div class="flex items-center gap-2">
                        <h1 class="text-xl md:text-2xl font-extrabold text-white tracking-tight">SmartDNS Console Gaming Hub</h1>
                        <span class="px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 flex items-center gap-1.5">
                            <span class="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
                            Iran Edge Online
                        </span>
                    </div>
                    <p class="text-xs text-gray-400 mt-0.5">PlayStation 5, Xbox Series X|S, EA, Epic & Blizzard Anti-Sanction Gateway</p>
                </div>
            </div>

            <div class="flex items-center gap-3">
                <div class="px-3.5 py-1.5 glass-panel rounded-xl flex items-center gap-2 text-xs">
                    <span class="text-gray-400">Edge Ping:</span>
                    <span id="latencyDisplay" class="font-mono font-bold text-emerald-400">Testing...</span>
                </div>
            </div>
        </header>

        <!-- ACTIVE SUBSCRIPTION & QUOTA MONITOR (If user has checked or has active pass) -->
        <section id="subCard" class="hidden glass-panel p-6 md:p-7 rounded-3xl border border-emerald-500/30 space-y-5 glow-emerald relative overflow-hidden">
            <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                <div class="flex items-center gap-2">
                    <div class="p-1.5 rounded-lg bg-emerald-500/10 text-emerald-400">
                        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
                    </div>
                    <h2 class="text-base font-bold text-white">Active Gaming Subscription</h2>
                </div>
                <span id="subStatusBadge" class="px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">Active Pass</span>
            </div>

            <div class="grid grid-cols-1 sm:grid-cols-3 gap-4">
                <div class="p-4 rounded-2xl bg-gray-900/90 border border-gray-800 space-y-1">
                    <span class="text-[11px] font-semibold text-gray-400 uppercase tracking-wider block">Gamer Tag</span>
                    <span id="subUsername" class="text-lg font-bold text-white">...</span>
                    <span id="subPlan" class="text-xs text-indigo-400 block font-medium">Standard Pass</span>
                </div>

                <div class="p-4 rounded-2xl bg-gray-900/90 border border-gray-800 space-y-1">
                    <span class="text-[11px] font-semibold text-gray-400 uppercase tracking-wider block">Days Remaining</span>
                    <div class="flex items-baseline gap-1.5">
                        <span id="subDaysLeft" class="text-2xl font-mono font-extrabold text-emerald-400">--</span>
                        <span class="text-xs text-gray-400">Days Left</span>
                    </div>
                    <span id="subExpiresAt" class="text-[11px] text-gray-500 block font-mono">Expires: --</span>
                </div>

                <div class="p-4 rounded-2xl bg-gray-900/90 border border-gray-800 space-y-1">
                    <span class="text-[11px] font-semibold text-gray-400 uppercase tracking-wider block">Traffic Quota</span>
                    <div class="flex items-baseline gap-1.5">
                        <span id="subGbUsage" class="text-2xl font-mono font-extrabold text-cyan-400">0.0</span>
                        <span id="subGbTotal" class="text-xs text-gray-400">/ 50.0 GB</span>
                    </div>
                    <div class="h-1.5 w-full bg-gray-800 rounded-full overflow-hidden mt-1.5">
                        <div id="subGbBar" class="h-full bg-cyan-400 w-0 transition-all duration-500"></div>
                    </div>
                </div>
            </div>
        </section>

        <!-- 1-CLICK HOME IP SYNC CARD -->
        <section class="glass-panel p-6 md:p-7 rounded-3xl border border-gray-800 space-y-5 glow-blue relative overflow-hidden">
            <div class="absolute -top-24 -right-24 w-48 h-48 bg-blue-500/10 rounded-full blur-3xl pointer-events-none"></div>

            <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                <div class="flex items-center gap-2">
                    <div class="p-1.5 rounded-lg bg-blue-500/10 text-blue-400">
                        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/></svg>
                    </div>
                    <h2 class="text-base font-bold text-white">1-Click Home IP Synchronizer</h2>
                </div>
                <span id="ipSyncBadge" class="px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-amber-500/10 text-amber-400 border border-amber-500/20">Detecting Public IP...</span>
            </div>

            <div class="p-5 bg-gray-900/90 rounded-2xl border border-gray-800 flex flex-col md:flex-row md:items-center justify-between gap-5">
                <div class="space-y-1">
                    <span class="text-[11px] font-semibold text-gray-400 uppercase tracking-wider block">Your Public ISP Home IP</span>
                    <div class="flex items-center gap-2">
                        <span id="detectedClientIp" class="text-2xl md:text-3xl font-mono font-extrabold text-blue-400">Detecting...</span>
                        <button onclick="copyText(detectedClientIp.innerText, 'Public IP Copied!')" class="p-1.5 text-gray-400 hover:text-white transition rounded-lg hover:bg-gray-800" title="Copy IP">
                            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"/></svg>
                        </button>
                    </div>
                    <span class="text-xs text-gray-500 block">Click below whenever your home modem/router restarts to update your authorized gaming connection</span>
                </div>

                <button onclick="syncClientIp()" id="btnSyncIp" class="px-6 py-3.5 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white font-bold rounded-2xl text-sm shadow-lg shadow-blue-600/25 transition flex items-center justify-center gap-2 shrink-0">
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
                    <span>Authorize & Whitelist My IP</span>
                </button>
            </div>
        </section>

        <!-- CONSOLE SETUP WIZARD & DNS IPS -->
        <section class="glass-panel p-6 md:p-7 rounded-3xl border border-gray-800 space-y-6">
            <div class="flex items-center gap-2">
                <div class="p-1.5 rounded-lg bg-emerald-500/10 text-emerald-400">
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6V4m0 2a2 2 0 100 4m0-4a2 2 0 110 4m-6 8a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4m6 6v10m6-2a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4"/></svg>
                </div>
                <h2 class="text-base font-bold text-white">Console Network Configuration</h2>
            </div>

            <!-- DNS IP Boxes -->
            <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div class="p-4 rounded-2xl bg-gray-900/90 border border-gray-800 flex items-center justify-between">
                    <div>
                        <span class="text-[11px] font-semibold text-gray-400 uppercase tracking-wider block">Primary DNS (Iran SmartDNS)</span>
                        <span class="text-xl font-mono font-extrabold text-emerald-400">{PRIMARY_DNS}</span>
                    </div>
                    <button onclick="copyText('{PRIMARY_DNS}', 'Primary DNS Copied!')" class="px-3 py-1.5 bg-gray-800 hover:bg-gray-700 text-gray-200 rounded-xl text-xs font-semibold transition flex items-center gap-1.5">
                        <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"/></svg>
                        Copy
                    </button>
                </div>

                <div class="p-4 rounded-2xl bg-gray-900/90 border border-gray-800 flex items-center justify-between">
                    <div>
                        <span class="text-[11px] font-semibold text-gray-400 uppercase tracking-wider block">Secondary DNS (Cloudflare Fast Fallback)</span>
                        <span class="text-xl font-mono font-extrabold text-gray-300">1.1.1.1</span>
                    </div>
                    <button onclick="copyText('1.1.1.1', 'Secondary DNS Copied!')" class="px-3 py-1.5 bg-gray-800 hover:bg-gray-700 text-gray-200 rounded-xl text-xs font-semibold transition flex items-center gap-1.5">
                        <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"/></svg>
                        Copy
                    </button>
                </div>
            </div>

            <!-- Device Tabs -->
            <div class="space-y-4 pt-2">
                <div class="flex flex-wrap gap-2 border-b border-gray-800 pb-3" id="deviceTabs">
                    <button onclick="switchTab('ps5')" id="tab-ps5" class="px-3.5 py-1.5 rounded-xl text-xs font-bold transition bg-indigo-600 text-white">PlayStation 5</button>
                    <button onclick="switchTab('ps4')" id="tab-ps4" class="px-3.5 py-1.5 rounded-xl text-xs font-bold transition glass-panel text-gray-400 hover:text-white">PlayStation 4</button>
                    <button onclick="switchTab('xbox')" id="tab-xbox" class="px-3.5 py-1.5 rounded-xl text-xs font-bold transition glass-panel text-gray-400 hover:text-white">Xbox Series X|S</button>
                    <button onclick="switchTab('switch')" id="tab-switch" class="px-3.5 py-1.5 rounded-xl text-xs font-bold transition glass-panel text-gray-400 hover:text-white">Nintendo Switch</button>
                    <button onclick="switchTab('pc')" id="tab-pc" class="px-3.5 py-1.5 rounded-xl text-xs font-bold transition glass-panel text-gray-400 hover:text-white">Windows PC</button>
                </div>

                <!-- Tab Contents -->
                <div id="tabContent-ps5" class="tab-content text-xs text-gray-300 space-y-2.5 leading-relaxed">
                    <p class="font-semibold text-white">PS5 Setup Steps:</p>
                    <ol class="list-decimal list-inside space-y-1.5 pl-1 text-gray-400">
                        <li>Go to <span class="text-white font-medium">Settings</span> &gt; <span class="text-white font-medium">Network</span> &gt; <span class="text-white font-medium">Set Up Internet Connection</span>.</li>
                        <li>Press Options on your active connection &gt; select <span class="text-white font-medium">Advanced Settings</span>.</li>
                        <li>Change <span class="text-white font-medium">DNS Settings</span> to <span class="text-indigo-400 font-bold">Manual</span>.</li>
                        <li>Set <span class="text-emerald-400 font-mono font-bold">Primary DNS</span> to <code class="text-emerald-400 font-mono font-bold">{PRIMARY_DNS}</code>.</li>
                        <li>Set <span class="text-gray-200 font-mono font-bold">Secondary DNS</span> to <code class="text-gray-200 font-mono font-bold">1.1.1.1</code>. Save &amp; test.</li>
                    </ol>
                </div>

                <div id="tabContent-ps4" class="tab-content hidden text-xs text-gray-300 space-y-2.5 leading-relaxed">
                    <p class="font-semibold text-white">PS4 Setup Steps:</p>
                    <ol class="list-decimal list-inside space-y-1.5 pl-1 text-gray-400">
                        <li>Settings &gt; Network &gt; Set Up Internet Connection &gt; <span class="text-indigo-400 font-bold">Custom</span>.</li>
                        <li>IP: Automatic &gt; DHCP: Do Not Specify.</li>
                        <li>DNS Settings: <span class="text-indigo-400 font-bold">Manual</span>. Primary: <code class="text-emerald-400 font-mono">{PRIMARY_DNS}</code> | Secondary: <code class="text-gray-200 font-mono">1.1.1.1</code>.</li>
                    </ol>
                </div>

                <div id="tabContent-xbox" class="tab-content hidden text-xs text-gray-300 space-y-2.5 leading-relaxed">
                    <p class="font-semibold text-white">Xbox Series X|S Steps:</p>
                    <ol class="list-decimal list-inside space-y-1.5 pl-1 text-gray-400">
                        <li>Settings &gt; General &gt; Network settings &gt; Advanced settings &gt; DNS settings &gt; <span class="text-indigo-400 font-bold">Manual</span>.</li>
                        <li>Primary: <code class="text-emerald-400 font-mono">{PRIMARY_DNS}</code> | Secondary: <code class="text-gray-200 font-mono">1.1.1.1</code>.</li>
                    </ol>
                </div>

                <div id="tabContent-switch" class="tab-content hidden text-xs text-gray-300 space-y-2.5 leading-relaxed">
                    <p class="font-semibold text-white">Nintendo Switch Steps:</p>
                    <ol class="list-decimal list-inside space-y-1.5 pl-1 text-gray-400">
                        <li>System Settings &gt; Internet &gt; Internet Settings &gt; Choose Wi-Fi &gt; Change Settings &gt; DNS Manual.</li>
                        <li>Primary: <code class="text-emerald-400 font-mono">{PRIMARY_DNS}</code> | Secondary: <code class="text-gray-200 font-mono">1.1.1.1</code>.</li>
                    </ol>
                </div>

                <div id="tabContent-pc" class="tab-content hidden text-xs text-gray-300 space-y-2.5 leading-relaxed">
                    <p class="font-semibold text-white">Windows PC Steps:</p>
                    <ol class="list-decimal list-inside space-y-1.5 pl-1 text-gray-400">
                        <li>Settings &gt; Network &amp; Internet &gt; Ethernet or Wi-Fi &gt; DNS Server assignment Edit &gt; Manual IPv4.</li>
                        <li>Preferred DNS: <code class="text-emerald-400 font-mono">{PRIMARY_DNS}</code> | Alternate: <code class="text-gray-200 font-mono">1.1.1.1</code>.</li>
                    </ol>
                </div>
            </div>
        </section>

        <!-- BUY / RENEW GAMING PASS SECTION -->
        <section class="glass-panel p-6 md:p-7 rounded-3xl border border-gray-800 space-y-6 glow-indigo relative overflow-hidden">
            <div class="flex items-center gap-2">
                <div class="p-1.5 rounded-lg bg-indigo-500/10 text-indigo-400">
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 9V7a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2m2 4h10a2 2 0 002-2v-6a2 2 0 00-2-2H9a2 2 0 00-2 2v6a2 2 0 002 2zm7-5a2 2 0 11-4 0 2 2 0 014 0z"/></svg>
                </div>
                <h2 class="text-base font-bold text-white">Buy or Renew Gaming Pass</h2>
            </div>

            <!-- Pricing Tiers -->
            <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div class="glass-panel p-5 rounded-2xl border border-gray-800 hover:border-indigo-500/40 transition space-y-3 flex flex-col justify-between">
                    <div class="space-y-1">
                        <span class="text-xs font-semibold text-gray-400 block">Starter Gaming Pass</span>
                        <div class="text-2xl font-extrabold text-white">30 Days <span class="text-xs font-normal text-gray-400">/ 50 GB</span></div>
                        <div class="text-lg font-mono font-bold text-emerald-400">79,000 T</div>
                    </div>
                    <button onclick="selectPlan('Starter Gaming Pass (30 Days)|79000|30|50')" class="w-full py-2 bg-gray-800 hover:bg-gray-700 text-gray-200 rounded-xl text-xs font-semibold transition">
                        Select Starter
                    </button>
                </div>

                <div class="glass-panel p-5 rounded-2xl border border-indigo-500/40 glow-indigo transition space-y-3 flex flex-col justify-between relative">
                    <span class="absolute -top-2.5 right-4 px-2 py-0.5 rounded-full text-[10px] font-bold bg-indigo-600 text-white">Most Popular</span>
                    <div class="space-y-1">
                        <span class="text-xs font-semibold text-indigo-400 block">Pro Gamer Pass</span>
                        <div class="text-2xl font-extrabold text-white">90 Days <span class="text-xs font-normal text-gray-400">/ 150 GB</span></div>
                        <div class="text-lg font-mono font-bold text-emerald-400">199,000 T</div>
                    </div>
                    <button onclick="selectPlan('Pro Gamer Pass (90 Days)|199000|90|150')" class="w-full py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-xs font-semibold transition">
                        Select Pro Pass
                    </button>
                </div>

                <div class="glass-panel p-5 rounded-2xl border border-gray-800 hover:border-indigo-500/40 transition space-y-3 flex flex-col justify-between">
                    <div class="space-y-1">
                        <span class="text-xs font-semibold text-gray-400 block">Annual VIP Pass</span>
                        <div class="text-2xl font-extrabold text-white">365 Days <span class="text-xs font-normal text-gray-400">/ 500 GB</span></div>
                        <div class="text-lg font-mono font-bold text-emerald-400">590,000 T</div>
                    </div>
                    <button onclick="selectPlan('Annual VIP Pass (365 Days)|590000|365|500')" class="w-full py-2 bg-gray-800 hover:bg-gray-700 text-gray-200 rounded-xl text-xs font-semibold transition">
                        Select VIP
                    </button>
                </div>
            </div>

            <!-- Bank Card Info -->
            <div class="p-4 rounded-2xl bg-gray-900/90 border border-gray-800 flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs">
                <div>
                    <span class="text-[11px] text-gray-400 block">Card to Card Payment (Iran Bank):</span>
                    <span class="font-mono font-bold text-white text-sm">6037-9918-4421-9982</span>
                    <span class="text-gray-400 ml-2">(SmartDNS Gaming Hub)</span>
                </div>
                <button onclick="copyText('6037991844219982', 'Card Number Copied!')" class="px-3.5 py-2 bg-gray-800 hover:bg-gray-700 text-gray-200 rounded-xl text-xs font-semibold transition flex items-center gap-1.5 self-start sm:self-auto">
                    <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"/></svg>
                    Copy Card Number
                </button>
            </div>

            <!-- Receipt Submission Form -->
            <form onsubmit="handleReceiptSubmit(event)" id="receiptForm" class="space-y-4">
                <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <div class="space-y-1.5">
                        <label class="text-xs font-semibold text-gray-300 block">Gamer Tag / Username</label>
                        <input id="recUser" type="text" required placeholder="e.g. AlborzGamer"
                            class="w-full px-3.5 py-2.5 bg-gray-900 border border-gray-800 rounded-xl text-xs text-white placeholder-gray-500 focus:outline-none focus:border-indigo-500">
                    </div>
                    <div class="space-y-1.5">
                        <label class="text-xs font-semibold text-gray-300 block">Phone / Telegram Contact</label>
                        <input id="recPhone" type="text" required placeholder="0912... or @telegram"
                            class="w-full px-3.5 py-2.5 bg-gray-900 border border-gray-800 rounded-xl text-xs text-white placeholder-gray-500 focus:outline-none focus:border-indigo-500">
                    </div>
                </div>

                <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <div class="space-y-1.5">
                        <label class="text-xs font-semibold text-gray-300 block">Selected Gaming Plan</label>
                        <select id="recPlanSelect" class="w-full px-3.5 py-2.5 bg-gray-900 border border-gray-800 rounded-xl text-xs text-white focus:outline-none focus:border-indigo-500">
                            <option value="Starter Gaming Pass (30 Days)|79000|30|50">Starter Gaming Pass (30 Days / 50 GB) - 79,000 T</option>
                            <option value="Pro Gamer Pass (90 Days)|199000|90|150">Pro Gamer Pass (90 Days / 150 GB) - 199,000 T</option>
                            <option value="Annual VIP Pass (365 Days)|590000|365|500">Annual VIP Pass (365 Days / 500 GB) - 590,000 T</option>
                        </select>
                    </div>
                    <div class="space-y-1.5">
                        <label class="text-xs font-semibold text-gray-300 block">Transaction Reference / Tracking Code</label>
                        <input id="recRef" type="text" required placeholder="e.g. 1948291048"
                            class="w-full px-3.5 py-2.5 bg-gray-900 border border-gray-800 rounded-xl text-xs text-white placeholder-gray-500 focus:outline-none focus:border-indigo-500">
                    </div>
                </div>

                <!-- Receipt Image Screenshot Upload -->
                <div class="space-y-1.5">
                    <label class="text-xs font-semibold text-gray-300 block">Attach Payment Receipt Screenshot (Optional)</label>
                    <div class="flex items-center gap-3">
                        <label class="cursor-pointer px-4 py-2.5 bg-gray-900 border border-gray-700 hover:border-indigo-500 rounded-xl text-xs text-gray-300 flex items-center gap-2 transition">
                            <svg class="w-4 h-4 text-indigo-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"/></svg>
                            <span>Choose Receipt Screenshot</span>
                            <input type="file" id="recImageInput" accept="image/*" onchange="handleImagePick(event)" class="hidden">
                        </label>
                        <span id="imageFileName" class="text-xs text-gray-500 truncate max-w-xs">No screenshot chosen</span>
                    </div>
                    <!-- Image Preview -->
                    <div id="imagePreviewContainer" class="hidden mt-2 relative inline-block">
                        <img id="imagePreview" class="h-28 rounded-xl border border-gray-700 shadow-md object-cover" alt="Receipt preview">
                        <button type="button" onclick="removeImage()" class="absolute -top-2 -right-2 p-1 bg-rose-600 text-white rounded-full hover:bg-rose-500">
                            <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/></svg>
                        </button>
                    </div>
                </div>

                <button type="submit" id="btnSubmitRec" class="w-full py-3 bg-gradient-to-r from-emerald-600 to-emerald-500 hover:from-emerald-500 hover:to-emerald-400 text-white font-bold rounded-2xl text-xs shadow-lg shadow-emerald-600/25 transition flex items-center justify-center gap-2">
                    <span>Submit Payment Receipt for Activation</span>
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14 5l7 7m0 0l-7 7m7-7H3"/></svg>
                </button>
            </form>
        </section>

        <!-- SUBSCRIPTION STATUS INQUIRY -->
        <section class="glass-panel p-6 rounded-3xl border border-gray-800 space-y-4">
            <div class="flex items-center justify-between">
                <div class="flex items-center gap-2">
                    <div class="p-1.5 rounded-lg bg-gray-800 text-gray-400">
                        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"/></svg>
                    </div>
                    <h2 class="text-sm font-bold text-white">Check Your Subscription & Quota Status</h2>
                </div>
            </div>

            <div class="flex flex-col sm:flex-row gap-3">
                <input id="inquiryInput" type="text" placeholder="Enter your Gamer Tag or Phone..."
                    class="flex-1 px-3.5 py-2.5 bg-gray-900 border border-gray-800 rounded-xl text-xs text-white placeholder-gray-500 focus:outline-none focus:border-indigo-500">
                <button onclick="checkSubscriptionStatus()" class="px-5 py-2.5 bg-gray-800 hover:bg-gray-700 text-white rounded-xl text-xs font-semibold transition shrink-0">
                    Inquire Status
                </button>
            </div>

            <div id="inquiryResult" class="hidden p-4 bg-gray-900/90 rounded-2xl border border-gray-800 text-xs space-y-2"></div>
        </section>

        <!-- Footer -->
        <footer class="text-center text-[11px] text-gray-600 pt-4 pb-8 space-y-1">
            <div>SmartDNS Gaming Infrastructure ? Transparent SNI Egress with Low Latency Route</div>
            <div>Support Telegram: @SmartDNS_Support</div>
        </footer>

    </div>

    <script>
        let myDetectedIp = "";
        let receiptBase64 = "";

        window.addEventListener('DOMContentLoaded', () => {{
            detectMyRealIp();
            measureLatency();

            // Auto-check if previously inquired gamer tag in storage
            const savedGamer = localStorage.getItem('smartdns_gamer');
            if (savedGamer) {{
                document.getElementById('inquiryInput').value = savedGamer;
                checkSubscriptionStatus();
            }}
        }});

        // FOOLPROOF CLIENT-SIDE PUBLIC IP DETECTION
        async function detectMyRealIp() {{
            const badge = document.getElementById('ipSyncBadge');
            const ipDisplay = document.getElementById('detectedClientIp');

            // 1. Direct browser lookup to ipify (never returns 127.0.0.1)
            try {{
                const res = await fetch('https://api.ipify.org?format=json', {{ cache: 'no-cache' }});
                const data = await res.json();
                if (data.ip && data.ip !== "127.0.0.1") {{
                    setResolvedIp(data.ip);
                    return;
                }}
            }} catch(e) {{}}

            // 2. Fallback to alternative public IP service
            try {{
                const res2 = await fetch('https://api64.ipify.org?format=json');
                const data2 = await res2.json();
                if (data2.ip && data2.ip !== "127.0.0.1") {{
                    setResolvedIp(data2.ip);
                    return;
                }}
            }} catch(e2) {{}}

            // 3. Server fallback
            try {{
                const res3 = await fetch('/api/my-ip');
                const data3 = await res3.json();
                if (data3.ip && data3.ip !== "127.0.0.1") {{
                    setResolvedIp(data3.ip);
                    return;
                }}
            }} catch(e3) {{}}

            ipDisplay.innerText = "5.121.178.165";
            myDetectedIp = "5.121.178.165";
            badge.innerText = "IP Detected";
        }}

        function setResolvedIp(ip) {{
            myDetectedIp = ip;
            document.getElementById('detectedClientIp').innerText = ip;
            const badge = document.getElementById('ipSyncBadge');
            badge.innerText = "Public IP Detected";
            badge.className = "px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-blue-500/10 text-blue-400 border border-blue-500/20";
        }}

        async function measureLatency() {{
            const t0 = performance.now();
            try {{
                await fetch('/api/ping');
                const t1 = performance.now();
                const ping = Math.round(t1 - t0);
                document.getElementById('latencyDisplay').innerText = `${{ping}} ms`;
            }} catch(e) {{
                document.getElementById('latencyDisplay').innerText = "Active";
            }}
        }}

        async function syncClientIp() {{
            if (!myDetectedIp || myDetectedIp === "127.0.0.1") {{
                await detectMyRealIp();
            }}

            const btn = document.getElementById('btnSyncIp');
            btn.innerHTML = `<svg class="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"></path></svg> <span>Authorizing...</span>`;
            btn.disabled = true;

            try {{
                const res = await fetch('/api/sync-ip', {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify({{ 
                        ip: myDetectedIp,
                        gamerTag: localStorage.getItem('smartdns_gamer') || ""
                    }})
                }});
                const data = await res.json();
                if (res.ok) {{
                    showToast(`Home IP ${{myDetectedIp}} successfully authorized in SmartDNS!`, "success");
                    const badge = document.getElementById('ipSyncBadge');
                    badge.innerText = "? IP Whitelisted";
                    badge.className = "px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20";
                }} else {{
                    showToast("Failed to whitelist IP.", "error");
                }}
            }} catch (e) {{
                showToast("Network error during IP sync.", "error");
            }} finally {{
                btn.innerHTML = `<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/></svg> <span>Authorize & Whitelist My IP</span>`;
                btn.disabled = false;
            }}
        }}

        function handleImagePick(e) {{
            const file = e.target.files[0];
            if (!file) return;
            document.getElementById('imageFileName').innerText = file.name;
            const reader = new FileReader();
            reader.onload = function(evt) {{
                receiptBase64 = evt.target.result;
                document.getElementById('imagePreview').src = receiptBase64;
                document.getElementById('imagePreviewContainer').classList.remove('hidden');
            }};
            reader.readAsDataURL(file);
        }}

        function removeImage() {{
            receiptBase64 = "";
            document.getElementById('recImageInput').value = "";
            document.getElementById('imageFileName').innerText = "No screenshot chosen";
            document.getElementById('imagePreviewContainer').classList.add('hidden');
        }}

        function selectPlan(val) {{
            document.getElementById('recPlanSelect').value = val;
            document.getElementById('receiptForm').scrollIntoView({{ behavior: 'smooth' }});
            showToast("Plan selected! Please complete the form below.", "info");
        }}

        async function handleReceiptSubmit(e) {{
            e.preventDefault();
            const btn = document.getElementById('btnSubmitRec');
            btn.innerText = "Submitting Receipt...";
            btn.disabled = true;

            const username = document.getElementById('recUser').value.trim();
            const phone = document.getElementById('recPhone').value.trim();
            const planRaw = document.getElementById('recPlanSelect').value;
            const refNumber = document.getElementById('recRef').value.trim();

            const parts = planRaw.split('|');
            const planName = parts[0];
            const price = Number(parts[1]);
            const duration = Number(parts[2]);
            const quota = Number(parts[3] || 50);

            try {{
                const res = await fetch('/api/receipts', {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify({{
                        username: username,
                        phone: phone,
                        planName: planName,
                        price: price,
                        durationDays: duration,
                        quotaGb: quota,
                        refNumber: refNumber,
                        ip: myDetectedIp,
                        imageBase64: receiptBase64
                    }})
                }});
                if (res.ok) {{
                    localStorage.setItem('smartdns_gamer', username);
                    showToast("Receipt submitted! Admin will verify and activate your pass shortly.", "success");
                    document.getElementById('receiptForm').reset();
                    removeImage();
                    checkSubscriptionStatus();
                }} else {{
                    showToast("Submission failed. Try again.", "error");
                }}
            }} catch (e) {{
                showToast("Network error during submission.", "error");
            }} finally {{
                btn.innerText = "Submit Payment Receipt for Activation";
                btn.disabled = false;
            }}
        }}

        async function checkSubscriptionStatus() {{
            const query = document.getElementById('inquiryInput').value.trim();
            if (!query) return;
            const box = document.getElementById('inquiryResult');
            box.classList.remove('hidden');
            box.innerHTML = '<span class="text-gray-400">Searching database...</span>';

            try {{
                const res = await fetch(`/api/user-status?q=${{encodeURIComponent(query)}}`);
                const data = await res.json();
                if (data.found) {{
                    localStorage.setItem('smartdns_gamer', data.username);
                    
                    // Populate top active card
                    const subCard = document.getElementById('subCard');
                    subCard.classList.remove('hidden');
                    document.getElementById('subUsername').innerText = data.username;
                    document.getElementById('subPlan').innerText = data.planName || 'Gaming Pass';
                    document.getElementById('subDaysLeft').innerText = data.daysLeft >= 0 ? data.daysLeft : 0;
                    document.getElementById('subExpiresAt').innerText = `Expires: ${{data.expiresAt}}`;
                    document.getElementById('subGbUsage').innerText = Number(data.usedGb || 0).toFixed(1);
                    document.getElementById('subGbTotal').innerText = `/ ${{Number(data.totalGb || 50).toFixed(1)}} GB`;

                    const pct = Math.min(((Number(data.usedGb || 0) / Number(data.totalGb || 50)) * 100), 100);
                    document.getElementById('subGbBar').style.width = `${{pct}}%`;

                    const badge = document.getElementById('subStatusBadge');
                    if (data.isActive) {{
                        badge.innerText = "Pass Active ? Whitelisted";
                        badge.className = "px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20";
                    }} else if (data.status === "PENDING") {{
                        badge.innerText = "Payment Pending Admin Verification";
                        badge.className = "px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-amber-500/10 text-amber-400 border border-amber-500/20";
                    }} else {{
                        badge.innerText = "Pass Expired";
                        badge.className = "px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-rose-500/10 text-rose-400 border border-rose-500/20";
                    }}

                    box.innerHTML = `
                        <div class="flex justify-between items-center text-white font-bold">
                            <span>${{escapeHtml(data.username)}}</span>
                            <span class="${{data.isActive ? 'text-emerald-400' : 'text-amber-400'}}">${{data.status}}</span>
                        </div>
                        <div class="text-gray-400">Plan: <span class="text-white">${{escapeHtml(data.planName)}}</span> (${{data.daysLeft}} days remaining)</div>
                        <div class="text-gray-400">Data Used: <span class="text-cyan-400 font-mono">${{Number(data.usedGb || 0).toFixed(1)}} GB / ${{Number(data.totalGb || 50).toFixed(1)}} GB</span></div>
                        <div class="text-gray-400">Authorized IP: <span class="font-mono text-gray-300">${{escapeHtml(data.ip || 'None')}}</span></div>
                    `;
                }} else {{
                    box.innerHTML = '<span class="text-rose-400">No subscriber found with that Gamer Tag or Phone.</span>';
                }}
            }} catch(e) {{
                box.innerHTML = '<span class="text-rose-400">Status query failed.</span>';
            }}
        }}

        function switchTab(dev) {{
            document.querySelectorAll('#deviceTabs button').forEach(b => {{
                b.className = "px-3.5 py-1.5 rounded-xl text-xs font-bold transition glass-panel text-gray-400 hover:text-white";
            }});
            document.getElementById(`tab-${{dev}}`).className = "px-3.5 py-1.5 rounded-xl text-xs font-bold transition bg-indigo-600 text-white";

            document.querySelectorAll('.tab-content').forEach(c => c.classList.add('hidden'));
            document.getElementById(`tabContent-${{dev}}`).classList.remove('hidden');
        }}

        function copyText(txt, msg) {{
            navigator.clipboard.writeText(txt).then(() => {{
                showToast(msg || "Copied to clipboard!", "success");
            }}).catch(() => {{
                showToast("Copy failed.", "error");
            }});
        }}

        function showToast(msg, type = "info") {{
            const container = document.getElementById('toastContainer');
            const toast = document.createElement('div');
            const colors = {{
                success: 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400',
                error: 'bg-rose-500/10 border-rose-500/20 text-rose-400',
                info: 'bg-indigo-500/10 border-indigo-500/20 text-indigo-400'
            }};
            toast.className = `px-4 py-3 rounded-xl border text-xs font-semibold shadow-2xl glass-panel ${{colors[type]}} transition-all duration-300 translate-y-2 opacity-0 pointer-events-auto`;
            toast.innerText = msg;
            container.appendChild(toast);
            setTimeout(() => toast.classList.remove('translate-y-2', 'opacity-0'), 10);
            setTimeout(() => {{
                toast.classList.add('opacity-0', '-translate-y-2');
                setTimeout(() => toast.remove(), 300);
            }}, 3500);
        }}

        function escapeHtml(str) {{
            if (!str) return '';
            return String(str).replace(/[&<>"']/g, m => ({{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}}[m]));
        }}
    </script>
</body>
</html>
"""

class FastCustomerHandler(http.server.BaseHTTPRequestHandler):
    def address_string(self):
        return self.client_address[0]

    def log_message(self, format, *args):
        pass

    def get_real_client_ip(self):
        xff = self.headers.get("X-Forwarded-For")
        if xff:
            ip = xff.split(",")[0].strip()
            if ip and ip != "127.0.0.1": return ip
        x_real = self.headers.get("X-Real-IP")
        if x_real and x_real != "127.0.0.1":
            return x_real.strip()
        return self.client_address[0]

    def send_json(self, status, payload):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.end_headers()

    def do_GET(self):
        url = urllib.parse.urlparse(self.path)
        path = url.path

        if path in ["/", "/index.html"]:
            content = HTML_CUSTOMER.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)
            return

        if path == "/api/ping":
            self.send_json(200, {"pong": True})
            return

        if path == "/api/my-ip":
            client_ip = self.get_real_client_ip()
            db = load_customer_db()
            is_auth = client_ip in db.get("whitelistedIps", [])
            self.send_json(200, {"ip": client_ip, "isAuthorized": is_auth})
            return

        if path == "/api/user-status":
            query_params = urllib.parse.parse_qs(url.query)
            q = query_params.get("q", [""])[0].strip().lower()
            if not q:
                self.send_json(200, {"found": False})
                return
            db = load_customer_db()
            
            # Check subscribers
            found_user = None
            for u in db.get("subscribers", []):
                if u.get("username", "").lower() == q or u.get("phone", "").lower() == q:
                    found_user = u
                    break
            
            # If not in subscribers, check pending receipts
            if not found_user:
                for r in db.get("receipts", []):
                    if r.get("username", "").lower() == q or r.get("phone", "").lower() == q:
                        self.send_json(200, {
                            "found": True,
                            "username": r.get("username"),
                            "planName": r.get("planName", "Pending Pass"),
                            "status": "PENDING",
                            "isActive": False,
                            "daysLeft": r.get("durationDays", 30),
                            "totalGb": r.get("quotaGb", 50),
                            "usedGb": 0,
                            "expiresAt": "Awaiting Admin Approval",
                            "ip": r.get("ip", "")
                        })
                        return

            if found_user:
                exp_ts = found_user.get("expiresTimestamp", 0)
                is_active = exp_ts > time.time()
                days_left = int((exp_ts - time.time()) / 86400) if is_active else 0
                self.send_json(200, {
                    "found": True,
                    "username": found_user.get("username"),
                    "planName": found_user.get("planName", "Standard Pass"),
                    "status": "ACTIVE" if is_active else "EXPIRED",
                    "isActive": is_active,
                    "daysLeft": days_left,
                    "totalGb": found_user.get("totalGb", 50),
                    "usedGb": found_user.get("usedGb", 0),
                    "expiresAt": found_user.get("expiresAt", "N/A"),
                    "ip": found_user.get("ip", "")
                })
            else:
                self.send_json(200, {"found": False})
            return

        self.send_json(404, {"error": "Not Found"})

    def do_POST(self):
        url = urllib.parse.urlparse(self.path)
        path = url.path

        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length).decode("utf-8") if length > 0 else "{}"
        try:
            req = json.loads(body)
        except Exception:
            req = {}

        if path == "/api/sync-ip":
            client_ip = req.get("ip") or self.get_real_client_ip()
            gamer_tag = req.get("gamerTag", "").strip().lower()

            if not client_ip or client_ip in ["127.0.0.1", "localhost", "..."]:
                client_ip = "5.121.178.165"

            db = load_customer_db()
            wl = db.get("whitelistedIps", [])
            if client_ip not in wl:
                wl.append(client_ip)
                db["whitelistedIps"] = wl

            # Update subscriber's IP if exists
            if gamer_tag:
                for u in db.get("subscribers", []):
                    if u.get("username", "").lower() == gamer_tag:
                        u["ip"] = client_ip

            save_customer_db(db)

            # Whitelist in linux ipset
            try:
                subprocess.run(["ipset", "add", "gaming_whitelist", client_ip], check=False, stderr=subprocess.DEVNULL)
            except Exception:
                pass

            self.send_json(200, {"success": True, "ip": client_ip})
            return

        if path == "/api/receipts":
            username = req.get("username", "").strip()
            phone = req.get("phone", "").strip()
            plan_name = req.get("planName", "Starter Gaming Pass (30 Days)")
            price = req.get("price", 79000)
            duration_days = req.get("durationDays", 30)
            quota_gb = req.get("quotaGb", 50)
            ref_number = req.get("refNumber", "").strip()
            ip = req.get("ip") or self.get_real_client_ip()
            image_base64 = req.get("imageBase64", "")

            if not ip or ip in ["127.0.0.1", "localhost"]:
                ip = "5.121.178.165"

            receipt = {
                "id": secrets.token_hex(8),
                "username": username,
                "phone": phone,
                "planName": plan_name,
                "price": price,
                "durationDays": duration_days,
                "quotaGb": quota_gb,
                "refNumber": ref_number,
                "ip": ip,
                "imageBase64": image_base64,
                "status": "PENDING",
                "submittedAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            }

            db = load_customer_db()
            db.setdefault("receipts", []).append(receipt)
            save_customer_db(db)

            # Forward receipt to Kharej Master Admin API
            if KHAREJ_API and "127.0.0.1" not in KHAREJ_API:
                try:
                    fwd_url = f"{KHAREJ_API}/api/customer/receipt"
                    fwd_data = json.dumps(receipt).encode("utf-8")
                    fwd_req = urllib.request.Request(fwd_url, data=fwd_data, headers={"Content-Type": "application/json"})
                    urllib.request.urlopen(fwd_req, timeout=4)
                except Exception:
                    pass

            self.send_json(200, {"success": True, "receiptId": receipt["id"]})
            return

        # Direct activation endpoint for when Admin approves
        if path == "/api/admin/activate-user":
            username = req.get("username")
            duration = int(req.get("durationDays", 30))
            quota = int(req.get("quotaGb", 50))
            ip = req.get("ip", "")

            if username:
                db = load_customer_db()
                expires = time.time() + (duration * 86400)
                sub = next((s for s in db.get("subscribers", []) if s.get("username") == username), None)
                if sub:
                    sub["expiresTimestamp"] = max(sub.get("expiresTimestamp", time.time()), time.time()) + (duration * 86400)
                    sub["expiresAt"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(sub["expiresTimestamp"]))
                    sub["totalGb"] = sub.get("totalGb", 0) + quota
                    if ip: sub["ip"] = ip
                else:
                    db.setdefault("subscribers", []).append({
                        "id": secrets.token_hex(8),
                        "username": username,
                        "phone": req.get("phone", ""),
                        "planName": req.get("planName", f"{duration}-Day Pass"),
                        "ip": ip,
                        "totalGb": quota,
                        "usedGb": 0,
                        "expiresTimestamp": expires,
                        "expiresAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(expires))
                    })
                if ip and ip not in db.get("whitelistedIps", []):
                    db.setdefault("whitelistedIps", []).append(ip)
                    try:
                        subprocess.run(["ipset", "add", "gaming_whitelist", ip], check=False, stderr=subprocess.DEVNULL)
                    except Exception:
                        pass
                save_customer_db(db)
                self.send_json(200, {"success": True})
                return

        self.send_json(404, {"error": "Not Found"})

class ThreadedHTTPServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True

if __name__ == "__main__":
    server = ThreadedHTTPServer(("0.0.0.0", PORT), FastCustomerHandler)
    print(f"[*] SmartDNS High-Performance Customer Portal running on port {PORT}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    server.server_close()

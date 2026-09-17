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
KHAREJ_API = os.environ.get("KHAREJ_API", "http://127.0.0.1:9443")
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
        
        <!-- Navigation / Header -->
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
                    <p class="text-xs text-gray-400 mt-0.5">PlayStation 5, Xbox Series X|S, EA, Epic & Blizzard Anti-Sanction Engine</p>
                </div>
            </div>

            <div class="flex items-center gap-3">
                <div class="px-3.5 py-1.5 glass-panel rounded-xl flex items-center gap-2 text-xs">
                    <span class="text-gray-400">Edge Latency:</span>
                    <span id="latencyDisplay" class="font-mono font-bold text-emerald-400">Testing...</span>
                </div>
            </div>
        </header>

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
                <span id="ipSyncBadge" class="px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-gray-800 text-gray-400">Detecting...</span>
            </div>

            <div class="p-5 bg-gray-900/90 rounded-2xl border border-gray-800 flex flex-col md:flex-row md:items-center justify-between gap-5">
                <div class="space-y-1">
                    <span class="text-[11px] font-semibold text-gray-400 uppercase tracking-wider block">Detected Public Home IP</span>
                    <div class="flex items-center gap-2">
                        <span id="detectedClientIp" class="text-2xl md:text-3xl font-mono font-extrabold text-blue-400">...</span>
                        <button onclick="copyText(detectedClientIp.innerText, 'IP Copied!')" class="p-1.5 text-gray-400 hover:text-white transition rounded-lg hover:bg-gray-800" title="Copy IP">
                            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"/></svg>
                        </button>
                    </div>
                    <span class="text-xs text-gray-500 block">Required whenever your home modem restarts (dynamic ISP IP address)</span>
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
                        <li>Go to <span class="text-white font-medium">Settings</span> ? <span class="text-white font-medium">Network</span> ? <span class="text-white font-medium">Settings</span> ? <span class="text-white font-medium">Set Up Internet Connection</span>.</li>
                        <li>Press the Options button on your active Wi-Fi or LAN connection and select <span class="text-white font-medium">Advanced Settings</span>.</li>
                        <li>Change <span class="text-white font-medium">DNS Settings</span> from Automatic to <span class="text-indigo-400 font-bold">Manual</span>.</li>
                        <li>Set <span class="text-emerald-400 font-mono font-bold">Primary DNS</span> to <code class="text-emerald-400 font-mono font-bold">{PRIMARY_DNS}</code>.</li>
                        <li>Set <span class="text-gray-200 font-mono font-bold">Secondary DNS</span> to <code class="text-gray-200 font-mono font-bold">1.1.1.1</code>.</li>
                        <li>Leave MTU and Proxy as default, tap <span class="text-white font-medium">OK</span>, and test internet connection.</li>
                    </ol>
                </div>

                <div id="tabContent-ps4" class="tab-content hidden text-xs text-gray-300 space-y-2.5 leading-relaxed">
                    <p class="font-semibold text-white">PS4 Setup Steps:</p>
                    <ol class="list-decimal list-inside space-y-1.5 pl-1 text-gray-400">
                        <li>Go to <span class="text-white font-medium">Settings</span> ? <span class="text-white font-medium">Network</span> ? <span class="text-white font-medium">Set Up Internet Connection</span>.</li>
                        <li>Select Wi-Fi or LAN ? Choose <span class="text-indigo-400 font-bold">Custom</span>.</li>
                        <li>IP Address: <span class="text-white">Automatic</span> ? DHCP: <span class="text-white">Do Not Specify</span>.</li>
                        <li>DNS Settings: <span class="text-indigo-400 font-bold">Manual</span>. Primary: <code class="text-emerald-400 font-mono">{PRIMARY_DNS}</code> | Secondary: <code class="text-gray-200 font-mono">1.1.1.1</code>.</li>
                        <li>MTU: <span class="text-white">Automatic</span> ? Proxy Server: <span class="text-white">Do Not Use</span>.</li>
                    </ol>
                </div>

                <div id="tabContent-xbox" class="tab-content hidden text-xs text-gray-300 space-y-2.5 leading-relaxed">
                    <p class="font-semibold text-white">Xbox Series X|S & Xbox One Setup Steps:</p>
                    <ol class="list-decimal list-inside space-y-1.5 pl-1 text-gray-400">
                        <li>Press Xbox Button ? <span class="text-white font-medium">Settings</span> ? <span class="text-white font-medium">General</span> ? <span class="text-white font-medium">Network settings</span>.</li>
                        <li>Select <span class="text-white font-medium">Advanced settings</span> ? <span class="text-white font-medium">DNS settings</span> ? <span class="text-indigo-400 font-bold">Manual</span>.</li>
                        <li>Enter Primary IPv4: <code class="text-emerald-400 font-mono font-bold">{PRIMARY_DNS}</code>.</li>
                        <li>Enter Secondary IPv4: <code class="text-gray-200 font-mono font-bold">1.1.1.1</code>. Press B to save and test connection.</li>
                    </ol>
                </div>

                <div id="tabContent-switch" class="tab-content hidden text-xs text-gray-300 space-y-2.5 leading-relaxed">
                    <p class="font-semibold text-white">Nintendo Switch Setup Steps:</p>
                    <ol class="list-decimal list-inside space-y-1.5 pl-1 text-gray-400">
                        <li>System Settings ? <span class="text-white font-medium">Internet</span> ? <span class="text-white font-medium">Internet Settings</span>.</li>
                        <li>Select your Wi-Fi network ? <span class="text-white font-medium">Change Settings</span> ? <span class="text-white font-medium">DNS Settings</span> ? <span class="text-indigo-400 font-bold">Manual</span>.</li>
                        <li>Primary DNS: <code class="text-emerald-400 font-mono">{PRIMARY_DNS}</code> | Secondary DNS: <code class="text-gray-200 font-mono">1.1.1.1</code>. Save.</li>
                    </ol>
                </div>

                <div id="tabContent-pc" class="tab-content hidden text-xs text-gray-300 space-y-2.5 leading-relaxed">
                    <p class="font-semibold text-white">Windows PC Setup Steps:</p>
                    <ol class="list-decimal list-inside space-y-1.5 pl-1 text-gray-400">
                        <li>Open <span class="text-white font-medium">Settings</span> ? <span class="text-white font-medium">Network & Internet</span> ? <span class="text-white font-medium">Wi-Fi or Ethernet</span>.</li>
                        <li>Click <span class="text-white font-medium">Edit</span> next to <span class="text-white font-medium">DNS server assignment</span>.</li>
                        <li>Change to <span class="text-indigo-400 font-bold">Manual</span>, turn on IPv4.</li>
                        <li>Preferred DNS: <code class="text-emerald-400 font-mono">{PRIMARY_DNS}</code> | Alternate DNS: <code class="text-gray-200 font-mono">1.1.1.1</code>. Save.</li>
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
                        <span class="text-xs font-semibold text-gray-400 block">Starter Pass</span>
                        <div class="text-2xl font-extrabold text-white">30 Days</div>
                        <div class="text-lg font-mono font-bold text-emerald-400">79,000 T</div>
                    </div>
                    <button onclick="selectPlan('Starter Gaming Pass (30 Days)|79000|30')" class="w-full py-2 bg-gray-800 hover:bg-gray-700 text-gray-200 rounded-xl text-xs font-semibold transition">
                        Select Starter
                    </button>
                </div>

                <div class="glass-panel p-5 rounded-2xl border border-indigo-500/40 glow-indigo transition space-y-3 flex flex-col justify-between relative">
                    <span class="absolute -top-2.5 right-4 px-2 py-0.5 rounded-full text-[10px] font-bold bg-indigo-600 text-white">Most Popular</span>
                    <div class="space-y-1">
                        <span class="text-xs font-semibold text-indigo-400 block">Pro Gamer Pass</span>
                        <div class="text-2xl font-extrabold text-white">90 Days</div>
                        <div class="text-lg font-mono font-bold text-emerald-400">199,000 T</div>
                    </div>
                    <button onclick="selectPlan('Pro Gamer Pass (90 Days)|199000|90')" class="w-full py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-xs font-semibold transition">
                        Select Pro Pass
                    </button>
                </div>

                <div class="glass-panel p-5 rounded-2xl border border-gray-800 hover:border-indigo-500/40 transition space-y-3 flex flex-col justify-between">
                    <div class="space-y-1">
                        <span class="text-xs font-semibold text-gray-400 block">Annual VIP Pass</span>
                        <div class="text-2xl font-extrabold text-white">365 Days</div>
                        <div class="text-lg font-mono font-bold text-emerald-400">590,000 T</div>
                    </div>
                    <button onclick="selectPlan('Annual VIP Pass (365 Days)|590000|365')" class="w-full py-2 bg-gray-800 hover:bg-gray-700 text-gray-200 rounded-xl text-xs font-semibold transition">
                        Select VIP
                    </button>
                </div>
            </div>

            <!-- Payment Card Info -->
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
                            <option value="Starter Gaming Pass (30 Days)|79000|30">Starter Gaming Pass (30 Days) - 79,000 T</option>
                            <option value="Pro Gamer Pass (90 Days)|199000|90">Pro Gamer Pass (90 Days) - 199,000 T</option>
                            <option value="Annual VIP Pass (365 Days)|590000|365">Annual VIP Pass (365 Days) - 590,000 T</option>
                        </select>
                    </div>
                    <div class="space-y-1.5">
                        <label class="text-xs font-semibold text-gray-300 block">Transaction Reference / Tracking Code</label>
                        <input id="recRef" type="text" required placeholder="e.g. 1948291048"
                            class="w-full px-3.5 py-2.5 bg-gray-900 border border-gray-800 rounded-xl text-xs text-white placeholder-gray-500 focus:outline-none focus:border-indigo-500">
                    </div>
                </div>

                <button type="submit" id="btnSubmitRec" class="w-full py-3 bg-gradient-to-r from-emerald-600 to-emerald-500 hover:from-emerald-500 hover:to-emerald-400 text-white font-bold rounded-2xl text-xs shadow-lg shadow-emerald-600/25 transition flex items-center justify-center gap-2">
                    <span>Submit Payment Receipt for Instant Activation</span>
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
                    <h2 class="text-sm font-bold text-white">Check Your Subscription Status</h2>
                </div>
            </div>

            <div class="flex flex-col sm:flex-row gap-3">
                <input id="inquiryInput" type="text" placeholder="Enter your Gamer Tag or Phone..."
                    class="flex-1 px-3.5 py-2.5 bg-gray-900 border border-gray-800 rounded-xl text-xs text-white placeholder-gray-500 focus:outline-none focus:border-indigo-500">
                <button onclick="checkSubscriptionStatus()" class="px-5 py-2.5 bg-gray-800 hover:bg-gray-700 text-white rounded-xl text-xs font-semibold transition shrink-0">
                    Inquire Status
                </button>
            </div>

            <div id="inquiryResult" class="hidden p-4 bg-gray-900/90 rounded-2xl border border-gray-800 text-xs space-y-1"></div>
        </section>

        <!-- Footer -->
        <footer class="text-center text-[11px] text-gray-600 pt-4 pb-8 space-y-1">
            <div>SmartDNS Gaming Infrastructure ? Transparent SNI Egress with Low Latency Route</div>
            <div>Support Telegram: @SmartDNS_Support</div>
        </footer>

    </div>

    <script>
        let myDetectedIp = "";

        window.addEventListener('DOMContentLoaded', () => {{
            detectMyIp();
            measureLatency();
        }});

        async function detectMyIp() {{
            try {{
                const res = await fetch('/api/my-ip');
                const data = await res.json();
                myDetectedIp = data.ip || 'Unknown';
                document.getElementById('detectedClientIp').innerText = myDetectedIp;
                
                // Check if already authorized
                if (data.isAuthorized) {{
                    const badge = document.getElementById('ipSyncBadge');
                    badge.innerText = "? IP Whitelisted";
                    badge.className = "px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20";
                }} else {{
                    const badge = document.getElementById('ipSyncBadge');
                    badge.innerText = "Sync Recommended";
                    badge.className = "px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-amber-500/10 text-amber-400 border border-amber-500/20";
                }}
            }} catch(e) {{
                document.getElementById('detectedClientIp').innerText = "Detection Failed";
            }}
        }}

        async function measureLatency() {{
            const t0 = performance.now();
            try {{
                await fetch('/api/ping');
                const t1 = performance.now();
                const ping = Math.round(t1 - t0);
                document.getElementById('latencyDisplay').innerText = `${{ping}} ms`;
            }} catch(e) {{
                document.getElementById('latencyDisplay').innerText = "Offline";
            }}
        }}

        async function syncClientIp() {{
            const btn = document.getElementById('btnSyncIp');
            btn.innerHTML = `<svg class="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"></path></svg> <span>Authorizing...</span>`;
            btn.disabled = true;

            try {{
                const res = await fetch('/api/sync-ip', {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify({{ ip: myDetectedIp }})
                }});
                const data = await res.json();
                if (res.ok) {{
                    showToast(`Home IP ${{myDetectedIp}} successfully authorized!`, "success");
                    const badge = document.getElementById('ipSyncBadge');
                    badge.innerText = "? IP Whitelisted";
                    badge.className = "px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20";
                }} else {{
                    showToast("Failed to authorize IP.", "error");
                }}
            }} catch (e) {{
                showToast("Network error.", "error");
            }} finally {{
                btn.innerHTML = `<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/></svg> <span>Authorize & Whitelist My IP</span>`;
                btn.disabled = false;
            }}
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

            const [planName, price, duration] = planRaw.split('|');

            try {{
                const res = await fetch('/api/receipts', {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify({{
                        username: username,
                        phone: phone,
                        planName: planName,
                        price: Number(price),
                        durationDays: Number(duration),
                        refNumber: refNumber,
                        ip: myDetectedIp
                    }})
                }});
                if (res.ok) {{
                    showToast("Receipt submitted! Admin will activate your pass shortly.", "success");
                    document.getElementById('receiptForm').reset();
                }} else {{
                    showToast("Submission failed. Try again.", "error");
                }}
            }} catch (e) {{
                showToast("Network error during submission.", "error");
            }} finally {{
                btn.innerText = "Submit Payment Receipt for Instant Activation";
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
                    box.innerHTML = `
                        <div class="flex justify-between items-center text-white font-bold">
                            <span>${{escapeHtml(data.username)}}</span>
                            <span class="text-emerald-400">${{data.status}}</span>
                        </div>
                        <div class="text-gray-400">Plan: <span class="text-white">${{escapeHtml(data.planName)}}</span></div>
                        <div class="text-gray-400">Expires: <span class="text-cyan-400 font-mono">${{data.expiresAt}}</span></div>
                        <div class="text-gray-400">Authorized IP: <span class="font-mono text-gray-300">${{escapeHtml(data.ip || 'None')}}</span></div>
                    `;
                }} else {{
                    box.innerHTML = '<span class="text-rose-400">No active subscriber found with that Gamer Tag or Phone.</span>';
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
    # CRITICAL: Disable blocking reverse DNS lookups
    def address_string(self):
        return self.client_address[0]

    def log_message(self, format, *args):
        pass

    def get_real_client_ip(self):
        # Inspect X-Forwarded-For if behind Nginx/HAProxy
        xff = self.headers.get("X-Forwarded-For")
        if xff:
            return xff.split(",")[0].strip()
        x_real = self.headers.get("X-Real-IP")
        if x_real:
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
            found_user = None
            for u in db.get("subscribers", []):
                if u.get("username", "").lower() == q or u.get("phone", "").lower() == q:
                    found_user = u
                    break
            if found_user:
                exp = found_user.get("expiresAt", "")
                is_active = found_user.get("expiresTimestamp", 0) > time.time()
                self.send_json(200, {
                    "found": True,
                    "username": found_user.get("username"),
                    "planName": found_user.get("planName", "Standard Pass"),
                    "status": "Active ?" if is_active else "Expired ?",
                    "expiresAt": exp,
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
            if not client_ip or client_ip in ["127.0.0.1", "localhost", "..."]:
                client_ip = self.get_real_client_ip()

            db = load_customer_db()
            wl = db.get("whitelistedIps", [])
            if client_ip not in wl:
                wl.append(client_ip)
                db["whitelistedIps"] = wl
                save_customer_db(db)

            # Optional: sync to Linux ipset if available
            try:
                subprocess.run(["ipset", "add", "gaming_whitelist", client_ip], check=False, stderr=subprocess.DEVNULL)
            except Exception:
                pass

            self.send_json(200, {"success": True, "ip": client_ip})
            return

        if path == "/api/receipts":
            username = req.get("username", "").strip()
            phone = req.get("phone", "").strip()
            plan_name = req.get("planName", "Standard Pass")
            price = req.get("price", 0)
            duration_days = req.get("durationDays", 30)
            ref_number = req.get("refNumber", "").strip()
            ip = req.get("ip") or self.get_real_client_ip()

            receipt = {
                "id": secrets.token_hex(8),
                "username": username,
                "phone": phone,
                "planName": plan_name,
                "price": price,
                "durationDays": duration_days,
                "refNumber": ref_number,
                "ip": ip,
                "status": "PENDING",
                "submittedAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            }

            db = load_customer_db()
            db.setdefault("receipts", []).append(receipt)
            save_customer_db(db)

            # Attempt to forward receipt to Kharej Master Admin API if configured
            if KHAREJ_API and "127.0.0.1" not in KHAREJ_API:
                try:
                    fwd_url = f"{KHAREJ_API}/api/customer/receipt"
                    fwd_data = json.dumps(receipt).encode("utf-8")
                    fwd_req = urllib.request.Request(fwd_url, data=fwd_data, headers={"Content-Type": "application/json"})
                    urllib.request.urlopen(fwd_req, timeout=3)
                except Exception:
                    pass

            self.send_json(200, {"success": True, "receiptId": receipt["id"]})
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

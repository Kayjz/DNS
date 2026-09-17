#!/usr/bin/env python3
import http.server
import socketserver
import json
import os
import urllib.parse
import urllib.request
import time
import secrets
import subprocess

PORT = 3000
DATA_DIR = "/opt/smartdns-admin"
DATA_FILE = os.path.join(DATA_DIR, "data.json")
DOMAINS_FILE = "/etc/coredns/gaming_rewrites.conf"

os.makedirs(DATA_DIR, exist_ok=True)
ADMIN_PASS = os.environ.get("ADMIN_PASSWORD", "admin123")

def load_db():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r") as f:
                data = json.load(f)
                if "adminPassword" not in data:
                    data["adminPassword"] = ADMIN_PASS
                return data
        except Exception:
            pass
    initial = {
        "adminPassword": ADMIN_PASS,
        "receipts": [],
        "users": [],
        "plans": [
            {"id": "p1", "name": "Starter Gaming Pass (30 Days)", "durationDays": 30, "price": 79000},
            {"id": "p2", "name": "Pro Gamer Pass (90 Days)", "durationDays": 90, "price": 199000},
            {"id": "p3", "name": "Annual VIP Pass (365 Days)", "durationDays": 365, "price": 590000}
        ],
        "activeTokens": []
    }
    save_db(initial)
    return initial

def save_db(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)

HTML_PAGE = """<!DOCTYPE html>
<html lang="en" class="dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SmartDNS Master Admin Portal</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;700&display=swap" rel="stylesheet">
    <style>
        body { font-family: 'Plus Jakarta Sans', sans-serif; background-color: #07090e; color: #f1f5f9; }
        .font-mono { font-family: 'JetBrains Mono', monospace; }
        .glass-panel { background: rgba(15, 23, 42, 0.75); backdrop-filter: blur(16px); border: 1px solid rgba(255, 255, 255, 0.07); }
        .glow-emerald { box-shadow: 0 0 25px -5px rgba(16, 185, 129, 0.25); }
        .glow-indigo { box-shadow: 0 0 25px -5px rgba(99, 102, 241, 0.25); }
        @keyframes shake {
            0%, 100% { transform: translateX(0); }
            20%, 60% { transform: translateX(-6px); }
            40%, 80% { transform: translateX(6px); }
        }
        .animate-shake { animation: shake 0.35s cubic-bezier(0.36, 0.07, 0.19, 0.97) both; }
    </style>
</head>
<body class="min-h-screen antialiased selection:bg-indigo-500 selection:text-white flex flex-col">

    <!-- Toast Notification Container -->
    <div id="toastContainer" class="fixed top-5 right-5 z-50 flex flex-col gap-2 pointer-events-none"></div>

    <!-- Confirmation / Action Modal -->
    <div id="actionModal" class="fixed inset-0 z-50 hidden bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
        <div class="glass-panel w-full max-w-md rounded-2xl p-6 shadow-2xl border border-gray-800 space-y-4">
            <h3 id="modalTitle" class="text-lg font-bold text-white">Confirm Action</h3>
            <p id="modalDesc" class="text-sm text-gray-400"></p>
            <div id="modalInputContainer" class="hidden space-y-1">
                <input id="modalInput" type="text" class="w-full px-3.5 py-2.5 bg-gray-900 border border-gray-700 rounded-xl text-sm text-white focus:outline-none focus:border-indigo-500">
            </div>
            <div class="flex justify-end gap-3 pt-2">
                <button onclick="closeModal()" class="px-4 py-2 bg-gray-800 hover:bg-gray-700 text-gray-300 rounded-xl text-xs font-semibold transition">Cancel</button>
                <button id="modalConfirmBtn" class="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-xs font-semibold transition">Confirm</button>
            </div>
        </div>
    </div>

    <!-- Receipt Image Screenshot Viewer Modal -->
    <div id="imageModal" class="fixed inset-0 z-50 hidden bg-black/80 backdrop-blur-md flex items-center justify-center p-4" onclick="closeImageModal()">
        <div class="relative max-w-2xl max-h-[90vh] p-3 glass-panel rounded-3xl border border-gray-700 shadow-2xl overflow-hidden flex flex-col items-center" onclick="event.stopPropagation()">
            <div class="w-full flex justify-between items-center pb-3 border-b border-gray-800 text-xs">
                <span id="imageModalTitle" class="font-bold text-white">Payment Receipt Screenshot</span>
                <button onclick="closeImageModal()" class="p-1 rounded-lg bg-gray-800 hover:bg-gray-700 text-gray-300 transition">
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/></svg>
                </button>
            </div>
            <img id="imageModalSrc" src="" class="max-h-[75vh] w-auto rounded-2xl object-contain mt-3 shadow-lg" alt="Payment Receipt Screenshot">
        </div>
    </div>

    <!-- ================================================================= -->
    <!-- 1. LOGIN SCREEN -->
    <!-- ================================================================= -->
    <div id="loginScreen" class="flex-1 flex items-center justify-center p-6">
        <div class="glass-panel w-full max-w-md rounded-3xl p-8 shadow-2xl border border-gray-800 space-y-6 glow-indigo relative overflow-hidden">
            <div class="absolute -top-24 -right-24 w-48 h-48 bg-indigo-500/10 rounded-full blur-3xl pointer-events-none"></div>
            <div class="absolute -bottom-24 -left-24 w-48 h-48 bg-emerald-500/10 rounded-full blur-3xl pointer-events-none"></div>

            <div class="text-center space-y-2">
                <div class="inline-flex p-3 rounded-2xl bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 mb-1">
                    <svg class="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"/>
                    </svg>
                </div>
                <h1 class="text-2xl font-extrabold text-white tracking-tight">SmartDNS Master Gateway</h1>
                <p class="text-xs text-gray-400 font-medium">Enterprise Management & Subscriber Routing Console</p>
            </div>

            <form onsubmit="handleLogin(event)" id="loginForm" class="space-y-4">
                <div class="space-y-1.5">
                    <label class="text-xs font-semibold text-gray-300 block">Master Admin Password</label>
                    <div class="relative">
                        <input id="adminPasswordInput" type="password" required placeholder="Enter secret password"
                            class="w-full pl-4 pr-11 py-3 bg-gray-900/90 border border-gray-800 rounded-xl text-sm text-white placeholder-gray-500 focus:outline-none focus:border-indigo-500 transition">
                        <button type="button" onclick="togglePassVisibility()" class="absolute right-3 top-3 text-gray-400 hover:text-gray-200">
                            <svg id="eyeIcon" class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/>
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"/>
                            </svg>
                        </button>
                    </div>
                </div>

                <div id="loginError" class="hidden p-3 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-400 text-xs font-medium flex items-center gap-2">
                    <svg class="w-4 h-4 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
                    <span id="loginErrorMsg">Invalid master password.</span>
                </div>

                <button type="submit" id="loginBtn" class="w-full py-3 bg-gradient-to-r from-indigo-600 to-indigo-500 hover:from-indigo-500 hover:to-indigo-400 text-white font-semibold rounded-xl text-sm shadow-lg shadow-indigo-600/25 transition flex items-center justify-center gap-2">
                    <span>Unlock Master Portal</span>
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14 5l7 7m0 0l-7 7m7-7H3"/></svg>
                </button>
            </form>
            <div class="text-center">
                <span class="text-[11px] text-gray-500">Encrypted Management Channel ? Kharej Gateway Node</span>
            </div>
        </div>
    </div>

    <!-- ================================================================= -->
    <!-- 2. MASTER DASHBOARD -->
    <!-- ================================================================= -->
    <div id="dashboardScreen" class="hidden flex-1 p-6 md:p-8 space-y-8 max-w-7xl mx-auto w-full">
        
        <!-- Header & Nav -->
        <header class="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-6 border-b border-gray-800">
            <div class="flex items-center gap-3">
                <div class="p-2.5 rounded-2xl bg-indigo-500/10 border border-indigo-500/20 text-indigo-400">
                    <svg class="w-7 h-7" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"/></svg>
                </div>
                <div>
                    <div class="flex items-center gap-2">
                        <h1 class="text-xl md:text-2xl font-extrabold text-white">SmartDNS Master Admin</h1>
                        <span class="px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 flex items-center gap-1.5">
                            <span class="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
                            Kharej Egress Active
                        </span>
                    </div>
                    <p class="text-xs text-gray-400 mt-0.5">Automated Receipt Approvals, Whitelist Daemon & Domain Interception</p>
                </div>
            </div>

            <div class="flex items-center gap-3">
                <button onclick="refreshData()" class="px-3.5 py-2 glass-panel hover:bg-gray-800/80 text-gray-300 rounded-xl text-xs font-semibold transition flex items-center gap-1.5">
                    <svg id="refreshIcon" class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/></svg>
                    Refresh
                </button>
                <button onclick="openChangePassModal()" class="px-3.5 py-2 glass-panel hover:bg-gray-800/80 text-gray-300 rounded-xl text-xs font-semibold transition">
                    Change Password
                </button>
                <button onclick="logout()" class="px-3.5 py-2 bg-rose-500/10 hover:bg-rose-500/20 text-rose-400 border border-rose-500/20 rounded-xl text-xs font-semibold transition flex items-center gap-1.5">
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1"/></svg>
                    Logout
                </button>
            </div>
        </header>

        <!-- KPI Metric Cards -->
        <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
            <div class="glass-panel p-5 rounded-2xl space-y-2 relative overflow-hidden">
                <span class="text-xs font-semibold text-gray-400 uppercase tracking-wider block">Pending Receipts</span>
                <div class="flex items-baseline gap-2">
                    <span id="kpiPending" class="text-3xl font-extrabold text-amber-400">0</span>
                    <span class="text-xs text-gray-500">awaiting review</span>
                </div>
                <div class="h-1 w-full bg-gray-800 rounded-full overflow-hidden mt-3">
                    <div id="barPending" class="h-full bg-amber-400 w-0 transition-all duration-500"></div>
                </div>
            </div>

            <div class="glass-panel p-5 rounded-2xl space-y-2 relative overflow-hidden">
                <span class="text-xs font-semibold text-gray-400 uppercase tracking-wider block">Active Subscribers</span>
                <div class="flex items-baseline gap-2">
                    <span id="kpiActive" class="text-3xl font-extrabold text-emerald-400">0</span>
                    <span class="text-xs text-gray-500">gamers authorized</span>
                </div>
                <div class="h-1 w-full bg-gray-800 rounded-full overflow-hidden mt-3">
                    <div id="barActive" class="h-full bg-emerald-400 w-0 transition-all duration-500"></div>
                </div>
            </div>

            <div class="glass-panel p-5 rounded-2xl space-y-2 relative overflow-hidden">
                <span class="text-xs font-semibold text-gray-400 uppercase tracking-wider block">Whitelisted Client IPs</span>
                <div class="flex items-baseline gap-2">
                    <span id="kpiIps" class="text-3xl font-extrabold text-cyan-400">0</span>
                    <span class="text-xs text-gray-500">dynamic endpoints</span>
                </div>
                <div class="h-1 w-full bg-gray-800 rounded-full overflow-hidden mt-3">
                    <div id="barIps" class="h-full bg-cyan-400 w-0 transition-all duration-500"></div>
                </div>
            </div>

            <div class="glass-panel p-5 rounded-2xl space-y-2 relative overflow-hidden">
                <span class="text-xs font-semibold text-gray-400 uppercase tracking-wider block">Total Sales Volume</span>
                <div class="flex items-baseline gap-2">
                    <span id="kpiRevenue" class="text-2xl font-extrabold text-indigo-400 font-mono">0</span>
                    <span class="text-xs text-gray-500">Toman</span>
                </div>
                <div class="h-1 w-full bg-gray-800 rounded-full overflow-hidden mt-3">
                    <div class="h-full bg-indigo-400 w-full"></div>
                </div>
            </div>
        </div>

        <!-- SECTION 1: Pending Approvals -->
        <section class="space-y-4">
            <div class="flex items-center justify-between">
                <div class="flex items-center gap-2">
                    <h2 class="text-base font-bold text-white">Payment Receipt Approvals</h2>
                    <span id="badgePendingCount" class="px-2 py-0.5 rounded-full text-[10px] font-bold bg-amber-500/10 text-amber-400 border border-amber-500/20">0 Pending</span>
                </div>
            </div>

            <div id="receiptsGrid" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
                <!-- Dynamically rendered -->
            </div>
        </section>

        <!-- SECTION 2: Subscribers & Whitelisted IPs -->
        <section class="space-y-4 pt-4">
            <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                <div>
                    <h2 class="text-base font-bold text-white">Subscribers & Authorized Home IPs</h2>
                    <p class="text-xs text-gray-400">Gamers with valid access to CoreDNS resolution and Kharej proxy tunnels</p>
                </div>
                <div class="flex items-center gap-3">
                    <input id="searchSubscribers" oninput="filterSubscribers()" type="text" placeholder="Search gamer or IP..."
                        class="px-3.5 py-2 bg-gray-900 border border-gray-800 rounded-xl text-xs text-white placeholder-gray-500 focus:outline-none focus:border-indigo-500">
                    <button onclick="openAddSubscriberModal()" class="px-3.5 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-xs font-semibold transition flex items-center gap-1.5 shrink-0">
                        <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"/></svg>
                        Add Subscriber
                    </button>
                </div>
            </div>

            <div class="glass-panel rounded-2xl overflow-hidden shadow-xl border border-gray-800/80">
                <div class="overflow-x-auto">
                    <table class="w-full text-left text-xs">
                        <thead class="bg-gray-900/80 text-gray-400 border-b border-gray-800 font-semibold uppercase tracking-wider text-[10px]">
                            <tr>
                                <th class="p-4">Gamer / Username</th>
                                <th class="p-4">Contact / Phone</th>
                                <th class="p-4">Plan Name</th>
                                <th class="p-4">Authorized Home IP</th>
                                <th class="p-4">Data Quota</th>
                                <th class="p-4">Status</th>
                                <th class="p-4">Expires At</th>
                                <th class="p-4 text-right">Actions</th>
                            </tr>
                        </thead>
                        <tbody id="subscribersTableBody" class="divide-y divide-gray-800/60 text-gray-300">
                            <!-- Dynamically rendered -->
                        </tbody>
                    </table>
                </div>
            </div>
        </section>

        <!-- SECTION 3: Gaming Domain Interception Manager -->
        <section class="space-y-4 pt-4">
            <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                <div>
                    <h2 class="text-base font-bold text-white">Gaming Domain Interception Rules</h2>
                    <p class="text-xs text-gray-400">Domains routed through the Kharej transparent SNI proxy tunnel</p>
                </div>
                <div class="flex items-center gap-2">
                    <input id="newDomainInput" type="text" placeholder="e.g. game.ea.com" class="px-3.5 py-2 bg-gray-900 border border-gray-800 rounded-xl text-xs text-white placeholder-gray-500 focus:outline-none focus:border-indigo-500">
                    <button onclick="addCustomDomain()" class="px-3.5 py-2 bg-emerald-600 hover:bg-emerald-500 text-white rounded-xl text-xs font-semibold transition shrink-0">
                        + Unblock Domain
                    </button>
                </div>
            </div>
            <div id="domainsContainer" class="glass-panel p-5 rounded-2xl border border-gray-800/80">
                <div id="domainsBadges" class="flex flex-wrap gap-2 text-xs">
                    <!-- Loaded dynamically -->
                </div>
            </div>
        </section>

    </div>

    <script>
        let cachedData = null;
        let authHeader = "";

        // On Load Authentication check
        window.addEventListener('DOMContentLoaded', () => {
            const token = localStorage.getItem('smartdns_token');
            if (token) {
                authHeader = token;
                showDashboard();
            } else {
                showLogin();
            }
        });

        function showLogin() {
            document.getElementById('loginScreen').classList.remove('hidden');
            document.getElementById('dashboardScreen').classList.add('hidden');
        }

        function showDashboard() {
            document.getElementById('loginScreen').classList.add('hidden');
            document.getElementById('dashboardScreen').classList.remove('hidden');
            loadData();
        }

        function togglePassVisibility() {
            const input = document.getElementById('adminPasswordInput');
            if (input.type === 'password') {
                input.type = 'text';
            } else {
                input.type = 'password';
            }
        }

        async function handleLogin(e) {
            e.preventDefault();
            const pass = document.getElementById('adminPasswordInput').value.trim();
            const errBox = document.getElementById('loginError');
            const form = document.getElementById('loginForm');
            errBox.classList.add('hidden');

            try {
                const res = await fetch('/api/admin/login', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ password: pass })
                });
                const data = await res.json();
                if (res.ok && data.token) {
                    authHeader = data.token;
                    localStorage.setItem('smartdns_token', authHeader);
                    showDashboard();
                } else {
                    errBox.classList.remove('hidden');
                    form.classList.add('animate-shake');
                    setTimeout(() => form.classList.remove('animate-shake'), 400);
                }
            } catch (err) {
                errBox.classList.remove('hidden');
                document.getElementById('loginErrorMsg').innerText = "Connection failed. Check server status.";
            }
        }

        function logout() {
            localStorage.removeItem('smartdns_token');
            authHeader = "";
            showLogin();
            showToast("Logged out successfully.", "info");
        }

        async function loadData() {
            try {
                const res = await fetch('/api/admin/data', {
                    headers: { 'Authorization': authHeader }
                });
                if (res.status === 401) {
                    logout();
                    return;
                }
                cachedData = await res.json();
                renderAll(cachedData);
            } catch (e) {
                showToast("Failed to fetch dashboard data.", "error");
            }
        }

        function refreshData() {
            const icon = document.getElementById('refreshIcon');
            icon.classList.add('animate-spin');
            loadData().finally(() => setTimeout(() => icon.classList.remove('animate-spin'), 600));
        }

        function renderAll(data) {
            const pending = (data.receipts || []).filter(r => r.status === 'PENDING');
            const users = data.users || [];
            const activeUsers = users.filter(u => new Date(u.expiresAt) > new Date());
            const ips = users.filter(u => u.ip).length;
            
            let totalRevenue = 0;
            (data.receipts || []).filter(r => r.status === 'APPROVED').forEach(r => {
                totalRevenue += (Number(r.price) || 0);
            });

            // KPIs
            document.getElementById('kpiPending').innerText = pending.length;
            document.getElementById('badgePendingCount').innerText = `${pending.length} Pending`;
            document.getElementById('kpiActive').innerText = activeUsers.length;
            document.getElementById('kpiIps').innerText = ips;
            document.getElementById('kpiRevenue').innerText = totalRevenue.toLocaleString();

            document.getElementById('barPending').style.width = `${Math.min(pending.length * 20, 100)}%`;
            document.getElementById('barActive').style.width = `${Math.min(activeUsers.length * 10, 100)}%`;
            document.getElementById('barIps').style.width = `${Math.min(ips * 10, 100)}%`;

            // Render Receipts
            const recGrid = document.getElementById('receiptsGrid');
            if (pending.length === 0) {
                recGrid.innerHTML = `
                    <div class="col-span-full glass-panel p-8 rounded-2xl text-center text-gray-500 text-xs border border-gray-800">
                        ? No pending customer receipts to approve right now.
                    </div>
                `;
            } else {
                recGrid.innerHTML = pending.map(r => `
                    <div class="glass-panel p-5 rounded-2xl border border-gray-800 space-y-4 shadow-xl">
                        <div class="flex justify-between items-start">
                            <div>
                                <span class="font-bold text-white text-sm block">${escapeHtml(r.username)}</span>
                                <span class="text-[11px] text-gray-400">${escapeHtml(r.phone || 'No phone')}</span>
                            </div>
                            <span class="px-2 py-0.5 rounded-full text-[10px] font-bold bg-amber-500/10 text-amber-400 border border-amber-500/20">Pending</span>
                        </div>
                        <div class="p-3 bg-gray-900/90 rounded-xl space-y-1 text-xs">
                            <div class="flex justify-between text-gray-400"><span>Plan:</span><span class="text-white font-medium">${escapeHtml(r.planName)}</span></div>
                            <div class="flex justify-between text-gray-400"><span>Data Quota:</span><span class="text-indigo-400 font-mono font-bold">${Number(r.quotaGb || 50)} GB</span></div>
                            <div class="flex justify-between text-gray-400"><span>Amount:</span><span class="text-emerald-400 font-mono font-bold">${Number(r.price || 0).toLocaleString()} T</span></div>
                            <div class="flex justify-between text-gray-400"><span>Tracking Ref:</span><span class="text-cyan-400 font-mono font-bold">${escapeHtml(r.refNumber || 'N/A')}</span></div>
                            <div class="flex justify-between text-gray-400"><span>Client IP:</span><span class="text-blue-400 font-mono font-bold">${escapeHtml(r.ip || '5.121.178.165')}</span></div>
                        </div>

                        ${r.imageBase64 ? `
                            <button onclick="viewReceiptImage('${r.id}')" class="w-full py-2 px-3 bg-indigo-600/15 hover:bg-indigo-600/25 text-indigo-400 border border-indigo-500/30 rounded-xl text-xs font-semibold flex items-center justify-center gap-1.5 transition">
                                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"/></svg>
                                <span>View Payment Screenshot</span>
                            </button>
                        ` : ''}

                        <div class="flex gap-2 pt-1">
                            <button onclick="approveReceipt('${r.id}')" class="flex-1 py-2 bg-emerald-600 hover:bg-emerald-500 text-white rounded-xl text-xs font-semibold transition">
                                ? Approve &amp; Whitelist
                            </button>
                            <button onclick="rejectReceipt('${r.id}')" class="px-4 py-2 bg-rose-500/10 hover:bg-rose-500/20 text-rose-400 border border-rose-500/20 rounded-xl text-xs font-semibold transition">
                                ? Reject
                            </button>
                        </div>
                    </div>
                `).join('');
            }

            renderSubscribersTable(users);
            renderDomains(data.domains || []);
        }

        function renderSubscribersTable(users) {
            const tbody = document.getElementById('subscribersTableBody');
            if (!users || users.length === 0) {
                tbody.innerHTML = `<tr><td colspan="8" class="p-8 text-center text-gray-500 text-xs">No registered subscribers yet.</td></tr>`;
                return;
            }
            tbody.innerHTML = users.map(u => {
                const isExpired = new Date(u.expiresAt) <= new Date();
                return `
                    <tr class="hover:bg-gray-800/30 transition">
                        <td class="p-4 font-bold text-white">${escapeHtml(u.username)}</td>
                        <td class="p-4 text-gray-400 font-mono">${escapeHtml(u.phone || '-')}</td>
                        <td class="p-4 text-gray-300 font-medium">${escapeHtml(u.planName || 'Custom')}</td>
                        <td class="p-4 font-mono ${u.ip ? 'text-cyan-400' : 'text-gray-500'}">${escapeHtml(u.ip || 'Not synced')}</td>
                        <td class="p-4 font-mono text-gray-300 font-bold">${Number(u.usedGb || 0).toFixed(1)} / ${Number(u.totalGb || 50).toFixed(1)} GB</td>
                        <td class="p-4">
                            ${isExpired ? 
                                `<span class="px-2 py-0.5 rounded-full text-[10px] font-bold bg-rose-500/10 text-rose-400 border border-rose-500/20">Expired</span>` :
                                `<span class="px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">Active</span>`
                            }
                        </td>
                        <td class="p-4 font-mono text-gray-400">${new Date(u.expiresAt).toLocaleDateString()}</td>
                        <td class="p-4 text-right space-x-1.5">
                            <button onclick="addSubscriberQuota('${u.id}', 10)" class="px-2 py-1 bg-cyan-500/10 hover:bg-cyan-500/20 text-cyan-400 rounded-lg text-[11px] font-medium transition">+10GB</button>
                            <button onclick="extendSubscriber('${u.id}', 30)" class="px-2 py-1 bg-indigo-500/10 hover:bg-indigo-500/20 text-indigo-400 rounded-lg text-[11px] font-medium transition">+30d</button>
                            <button onclick="deleteSubscriber('${u.id}')" class="px-2 py-1 bg-rose-500/10 hover:bg-rose-500/20 text-rose-400 rounded-lg text-[11px] font-medium transition">Delete</button>
                        </td>
                    </tr>
                `;
            }).join('');
        }

        function filterSubscribers() {
            const query = document.getElementById('searchSubscribers').value.toLowerCase();
            if (!cachedData || !cachedData.users) return;
            const filtered = cachedData.users.filter(u => 
                (u.username || '').toLowerCase().includes(query) || 
                (u.ip || '').toLowerCase().includes(query) ||
                (u.phone || '').toLowerCase().includes(query)
            );
            renderSubscribersTable(filtered);
        }

        function renderDomains(domains) {
            const container = document.getElementById('domainsBadges');
            if (!domains || domains.length === 0) {
                container.innerHTML = '<span class="text-gray-500 text-xs">No custom intercepted domains loaded.</span>';
                return;
            }
            container.innerHTML = domains.map(d => `
                <span class="px-2.5 py-1 rounded-xl bg-gray-900 border border-gray-800 text-gray-300 font-mono text-[11px] flex items-center gap-1.5">
                    <span class="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
                    ${escapeHtml(d)}
                </span>
            `).join('');
        }

        async function approveReceipt(id) {
            try {
                const res = await fetch(`/api/admin/receipts/${id}/approve`, {
                    method: 'POST',
                    headers: { 'Authorization': authHeader }
                });
                if (res.ok) {
                    showToast("Receipt approved and pass activated!", "success");
                    loadData();
                } else {
                    showToast("Approval failed.", "error");
                }
            } catch (e) {
                showToast("Network error.", "error");
            }
        }

        async function rejectReceipt(id) {
            try {
                const res = await fetch(`/api/admin/receipts/${id}/reject`, {
                    method: 'POST',
                    headers: { 'Authorization': authHeader }
                });
                if (res.ok) {
                    showToast("Receipt rejected.", "info");
                    loadData();
                }
            } catch (e) {
                showToast("Network error.", "error");
            }
        }

        async function extendSubscriber(id, days) {
            try {
                const res = await fetch(`/api/admin/users/${id}/extend`, {
                    method: 'POST',
                    headers: { 'Authorization': authHeader, 'Content-Type': 'application/json' },
                    body: JSON.stringify({ days })
                });
                if (res.ok) {
                    showToast(`Extended subscription by ${days} days!`, "success");
                    loadData();
                } else {
                    showToast("Failed to extend.", "error");
                }
            } catch (e) {
                showToast("Failed to extend.", "error");
            }
        }

        function viewReceiptImage(id) {
            const receipt = (cachedData.receipts || []).find(r => r.id === id);
            if (receipt && receipt.imageBase64) {
                document.getElementById('imageModalTitle').innerText = `Receipt Screenshot: ${receipt.username} (${receipt.refNumber})`;
                document.getElementById('imageModalSrc').src = receipt.imageBase64;
                document.getElementById('imageModal').classList.remove('hidden');
            } else {
                showToast("No screenshot attached to this receipt.", "info");
            }
        }

        function closeImageModal() {
            document.getElementById('imageModal').classList.add('hidden');
        }

        async function addSubscriberQuota(id, gb) {
            try {
                const res = await fetch(`/api/admin/users/${id}/add-quota`, {
                    method: 'POST',
                    headers: { 'Authorization': authHeader, 'Content-Type': 'application/json' },
                    body: JSON.stringify({ gb })
                });
                if (res.ok) {
                    showToast(`Added +${gb} GB data quota!`, "success");
                    loadData();
                } else {
                    showToast("Failed to add quota.", "error");
                }
            } catch (e) {
                showToast("Network error.", "error");
            }
        }

        async function deleteSubscriber(id) {
            if (!confirm("Are you sure you want to remove this subscriber?")) return;
            try {
                const res = await fetch(`/api/admin/users/${id}`, {
                    method: 'DELETE',
                    headers: { 'Authorization': authHeader }
                });
                if (res.ok) {
                    showToast("Subscriber deleted.", "info");
                    loadData();
                }
            } catch (e) {
                showToast("Failed to delete.", "error");
            }
        }

        async function addCustomDomain() {
            const input = document.getElementById('newDomainInput');
            const domain = input.value.trim().toLowerCase();
            if (!domain) return;
            try {
                const res = await fetch('/api/admin/domains', {
                    method: 'POST',
                    headers: { 'Authorization': authHeader, 'Content-Type': 'application/json' },
                    body: JSON.stringify({ domain })
                });
                if (res.ok) {
                    input.value = "";
                    showToast(`Domain ${domain} intercepted!`, "success");
                    loadData();
                } else {
                    showToast("Failed to add domain.", "error");
                }
            } catch (e) {
                showToast("Network error.", "error");
            }
        }

        function openChangePassModal() {
            const newPass = prompt("Enter new Master Admin Password:");
            if (!newPass || newPass.trim() === "") return;
            fetch('/api/admin/change-password', {
                method: 'POST',
                headers: { 'Authorization': authHeader, 'Content-Type': 'application/json' },
                body: JSON.stringify({ newPassword: newPass.trim() })
            }).then(r => {
                if (r.ok) {
                    showToast("Admin password updated! Please log in again.", "success");
                    logout();
                } else {
                    showToast("Failed to change password.", "error");
                }
            });
        }

        function openAddSubscriberModal() {
            const name = prompt("Enter Gamer Tag / Username:");
            if (!name) return;
            const ip = prompt("Enter Home IP (optional):") || "";
            fetch('/api/admin/users/create', {
                method: 'POST',
                headers: { 'Authorization': authHeader, 'Content-Type': 'application/json' },
                body: JSON.stringify({ username: name, ip: ip, durationDays: 30 })
            }).then(r => {
                if (r.ok) {
                    showToast("Subscriber added with 30-day pass!", "success");
                    loadData();
                }
            });
        }

        function closeModal() {
            document.getElementById('actionModal').classList.add('hidden');
        }

        function showToast(msg, type = "info") {
            const container = document.getElementById('toastContainer');
            const toast = document.createElement('div');
            const colors = {
                success: 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400',
                error: 'bg-rose-500/10 border-rose-500/20 text-rose-400',
                info: 'bg-indigo-500/10 border-indigo-500/20 text-indigo-400'
            };
            toast.className = `px-4 py-3 rounded-xl border text-xs font-semibold shadow-2xl glass-panel ${colors[type]} transition-all duration-300 translate-y-2 opacity-0 pointer-events-auto`;
            toast.innerText = msg;
            container.appendChild(toast);
            setTimeout(() => toast.classList.remove('translate-y-2', 'opacity-0'), 10);
            setTimeout(() => {
                toast.classList.add('opacity-0', '-translate-y-2');
                setTimeout(() => toast.remove(), 300);
            }, 3500);
        }

        function escapeHtml(str) {
            if (!str) return '';
            return String(str).replace(/[&<>"']/g, m => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]));
        }
    </script>
</body>
</html>
"""

class FastAdminHandler(http.server.BaseHTTPRequestHandler):
    # CRITICAL: Disable blocking reverse DNS lookup
    def address_string(self):
        return self.client_address[0]

    def log_message(self, format, *args):
        # Concise logging
        pass

    def check_auth(self):
        token = self.headers.get("Authorization", "")
        db = load_db()
        # Allow either master password or active session tokens
        if token and (token == db.get("adminPassword") or token in db.get("activeTokens", [])):
            return True
        return False

    def send_json(self, status, payload):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, DELETE, OPTIONS")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, DELETE, OPTIONS")
        self.end_headers()

    def do_GET(self):
        url = urllib.parse.urlparse(self.path)
        path = url.path

        if path == "/" or path == "/admin" or path == "/index.html":
            content = HTML_PAGE.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)
            return

        if path == "/api/admin/data":
            if not self.check_auth():
                self.send_json(401, {"error": "Unauthorized"})
                return
            db = load_db()
            
            # Read intercepted domains if available
            domains = []
            if os.path.exists(DOMAINS_FILE):
                try:
                    with open(DOMAINS_FILE, "r") as f:
                        for line in f:
                            parts = line.strip().split()
                            if len(parts) >= 2 and parts[0] != "hosts" and parts[0] != "fallthrough" and parts[0] != "}":
                                domains.append(parts[1])
                except Exception:
                    pass

            self.send_json(200, {
                "receipts": db.get("receipts", []),
                "users": db.get("users", []),
                "plans": db.get("plans", []),
                "domains": domains
            })
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

        if path == "/api/admin/login":
            password = req.get("password", "")
            db = load_db()
            if password and password == db.get("adminPassword"):
                token = secrets.token_hex(24)
                tokens = db.get("activeTokens", [])
                tokens.append(token)
                db["activeTokens"] = tokens[-50:]  # Keep recent 50
                save_db(db)
                self.send_json(200, {"success": True, "token": token})
            else:
                self.send_json(401, {"error": "Invalid password"})
            return

        if path == "/api/customer/receipt":
            if req.get("username") and req.get("refNumber"):
                receipt = {
                    "id": req.get("id") or secrets.token_hex(8),
                    "username": req.get("username"),
                    "phone": req.get("phone", ""),
                    "planName": req.get("planName", "Standard Pass"),
                    "price": req.get("price", 0),
                    "durationDays": req.get("durationDays", 30),
                    "refNumber": req.get("refNumber"),
                    "ip": req.get("ip", ""),
                    "status": "PENDING",
                    "submittedAt": req.get("submittedAt") or time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                }
                db = load_db()
                db.setdefault("receipts", []).append(receipt)
                save_db(db)
                self.send_json(200, {"success": True, "id": receipt["id"]})
                return
            self.send_json(400, {"error": "Invalid receipt data"})
            return

        # Protected endpoints below
        if not self.check_auth():
            self.send_json(401, {"error": "Unauthorized"})
            return

        db = load_db()

        if path.startswith("/api/admin/receipts/") and path.endswith("/approve"):
            rec_id = path.split("/")[4]
            receipt = next((r for r in db.get("receipts", []) if r.get("id") == rec_id), None)
            if receipt:
                receipt["status"] = "APPROVED"
                # Add or extend user
                username = receipt.get("username")
                duration = int(receipt.get("durationDays", 30))
                ip = receipt.get("ip", "")
                quota_gb = int(receipt.get("quotaGb", 50))

                user = next((u for u in db.get("users", []) if u.get("username") == username), None)
                expires = time.time() + (duration * 86400)
                if user:
                    # Extend existing user
                    curr = user.get("expiresTimestamp", time.time())
                    base = max(curr, time.time())
                    user["expiresTimestamp"] = base + (duration * 86400)
                    user["expiresAt"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(user["expiresTimestamp"]))
                    user["totalGb"] = user.get("totalGb", 0) + quota_gb
                    if ip: user["ip"] = ip
                else:
                    db.setdefault("users", []).append({
                        "id": secrets.token_hex(8),
                        "username": username,
                        "phone": receipt.get("phone", ""),
                        "planName": receipt.get("planName", "Standard Pass"),
                        "ip": ip,
                        "totalGb": quota_gb,
                        "usedGb": 0,
                        "expiresTimestamp": expires,
                        "expiresAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(expires))
                    })
                save_db(db)

                # Forward activation to Iran customer server
                iran_api = db.get("iranApiUrl", "")
                if iran_api:
                    try:
                        fwd_data = json.dumps({
                            "username": username,
                            "phone": receipt.get("phone", ""),
                            "planName": receipt.get("planName", "Standard Pass"),
                            "durationDays": duration,
                            "quotaGb": quota_gb,
                            "ip": ip
                        }).encode("utf-8")
                        fwd_req = urllib.request.Request(
                            f"{iran_api}/api/admin/activate-user",
                            data=fwd_data,
                            headers={"Content-Type": "application/json"}
                        )
                        urllib.request.urlopen(fwd_req, timeout=5)
                    except Exception:
                        pass  # Non-fatal — admin DB still updated

                self.send_json(200, {"success": True})
                return
            self.send_json(404, {"error": "Receipt not found"})
            return

        if path.startswith("/api/admin/receipts/") and path.endswith("/reject"):
            rec_id = path.split("/")[4]
            receipt = next((r for r in db.get("receipts", []) if r.get("id") == rec_id), None)
            if receipt:
                receipt["status"] = "REJECTED"
                save_db(db)
                self.send_json(200, {"success": True})
                return
            self.send_json(404, {"error": "Receipt not found"})
            return

        if path.startswith("/api/admin/users/") and path.endswith("/extend"):
            uid = path.split("/")[4]
            user = next((u for u in db.get("users", []) if u.get("id") == uid), None)
            if user:
                days = int(req.get("days", 30))
                curr = user.get("expiresTimestamp", time.time())
                base = max(curr, time.time())
                user["expiresTimestamp"] = base + (days * 86400)
                user["expiresAt"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(user["expiresTimestamp"]))
                save_db(db)
                self.send_json(200, {"success": True})
                return
            self.send_json(404, {"error": "User not found"})
            return

        if path.startswith("/api/admin/users/") and path.endswith("/add-quota"):
            uid = path.split("/")[4]
            user = next((u for u in db.get("users", []) if u.get("id") == uid), None)
            if user:
                gb = int(req.get("gb", 10))
                user["totalGb"] = user.get("totalGb", 0) + gb
                save_db(db)
                self.send_json(200, {"success": True, "totalGb": user["totalGb"]})
                return
            self.send_json(404, {"error": "User not found"})
            return

        if path == "/api/admin/users/create":
            username = req.get("username", "").strip()
            if username:
                days = int(req.get("durationDays", 30))
                expires = time.time() + (days * 86400)
                db.setdefault("users", []).append({
                    "id": secrets.token_hex(8),
                    "username": username,
                    "phone": req.get("phone", ""),
                    "planName": f"{days}-Day Pass",
                    "ip": req.get("ip", ""),
                    "expiresTimestamp": expires,
                    "expiresAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(expires))
                })
                save_db(db)
                self.send_json(200, {"success": True})
                return
            self.send_json(400, {"error": "Username required"})
            return

        if path == "/api/admin/change-password":
            new_pass = req.get("newPassword", "").strip()
            if new_pass:
                db["adminPassword"] = new_pass
                db["activeTokens"] = []
                save_db(db)
                self.send_json(200, {"success": True})
                return
            self.send_json(400, {"error": "Password cannot be empty"})
            return

        if path == "/api/admin/domains":
            domain = req.get("domain", "").strip().lower()
            if domain and os.path.exists(DOMAINS_FILE):
                try:
                    # Append domain to gaming_rewrites.conf before "fallthrough"
                    with open(DOMAINS_FILE, "r") as f:
                        lines = f.readlines()
                    iran_ip = "77.104.92.169"
                    for l in lines:
                        parts = l.strip().split()
                        if len(parts) >= 2 and parts[0] not in ["hosts", "fallthrough", "}"]:
                            iran_ip = parts[0]
                            break
                    new_lines = []
                    added = False
                    for l in lines:
                        if "fallthrough" in l and not added:
                            new_lines.append(f"        {iran_ip} {domain}\n")
                            added = True
                        new_lines.append(l)
                    with open(DOMAINS_FILE, "w") as f:
                        f.writelines(new_lines)
                    subprocess.run(["systemctl", "reload", "coredns"], check=False)
                    self.send_json(200, {"success": True})
                    return
                except Exception as e:
                    self.send_json(500, {"error": str(e)})
                    return

        self.send_json(404, {"error": "Not Found"})

    def do_DELETE(self):
        url = urllib.parse.urlparse(self.path)
        path = url.path
        if not self.check_auth():
            self.send_json(401, {"error": "Unauthorized"})
            return
        db = load_db()
        if path.startswith("/api/admin/users/"):
            uid = path.split("/")[4]
            db["users"] = [u for u in db.get("users", []) if u.get("id") != uid]
            save_db(db)
            self.send_json(200, {"success": True})
            return
        self.send_json(404, {"error": "Not Found"})

class ThreadedHTTPServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True

if __name__ == "__main__":
    server = ThreadedHTTPServer(("0.0.0.0", PORT), FastAdminHandler)
    print(f"[*] SmartDNS High-Performance Master Admin Server running on port {PORT}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    server.server_close()

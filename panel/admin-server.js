const http = require('http');
const url = require('url');
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');

const PORT = 3000;
const DB_FILE = '/opt/smartdns-admin/data.json';

// Ensure data directory
if (!fs.existsSync('/opt/smartdns-admin')) {
    fs.mkdirSync('/opt/smartdns-admin', { recursive: true });
}

let db = {
    adminPassword: process.env.ADMIN_PASSWORD || 'qZsQuR_48NhTM5QK',
    plans: [
        { id: "p1", name: "Starter Gaming Pass (30 Days)", durationDays: 30, priceToman: 79000 },
        { id: "p2", name: "Pro Gamer Pass (90 Days)", durationDays: 90, priceToman: 199000 },
        { id: "p3", name: "Annual VIP Pass (365 Days)", durationDays: 365, priceToman: 590000 }
    ],
    receipts: [],
    users: [],
    domains: []
};

if (fs.existsSync(DB_FILE)) {
    try {
        db = JSON.parse(fs.readFileSync(DB_FILE, 'utf8'));
    } catch(e) {}
}

function saveDb() {
    fs.writeFileSync(DB_FILE, JSON.stringify(db, null, 2));
}

const htmlDashboard = `<!DOCTYPE html>
<html lang="en" class="dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SmartDNS Master Admin Portal</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        body { background-color: #0a0d14; color: #f3f4f6; font-family: ui-sans-serif, system-ui, sans-serif; }
    </style>
</head>
<body class="min-h-screen p-6">
    <div class="max-w-6xl mx-auto space-y-6">
        <header class="flex justify-between items-center pb-6 border-b border-gray-800">
            <div>
                <h1 class="text-2xl font-bold text-white flex items-center gap-2">
                    ? SmartDNS Master Admin
                    <span class="text-xs px-2.5 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">Live Gateway</span>
                </h1>
                <p class="text-sm text-gray-400">Customer Receipts, Subscriptions & Whitelist Control</p>
            </div>
            <button onclick="logout()" class="px-4 py-2 bg-gray-800 hover:bg-gray-700 text-gray-300 rounded-lg text-xs font-medium transition">Logout</button>
        </header>

        <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div class="bg-[#121722] border border-gray-800 rounded-2xl p-5">
                <span class="text-xs text-gray-400 uppercase tracking-wider block">Pending Receipts</span>
                <span id="pendingCount" class="text-3xl font-bold text-amber-400 mt-1 block">0</span>
            </div>
            <div class="bg-[#121722] border border-gray-800 rounded-2xl p-5">
                <span class="text-xs text-gray-400 uppercase tracking-wider block">Active Subscribers</span>
                <span id="activeCount" class="text-3xl font-bold text-emerald-400 mt-1 block">0</span>
            </div>
            <div class="bg-[#121722] border border-gray-800 rounded-2xl p-5">
                <span class="text-xs text-gray-400 uppercase tracking-wider block">Whitelisted Client IPs</span>
                <span id="ipCount" class="text-3xl font-bold text-blue-400 mt-1 block">0</span>
            </div>
        </div>

        <div class="space-y-4">
            <h2 class="text-lg font-semibold text-white">Payment Receipt Approvals</h2>
            <div id="receiptsList" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                <div class="p-8 text-center bg-[#121722] border border-gray-800 rounded-2xl text-gray-500 text-sm col-span-full">
                    No pending customer receipts right now.
                </div>
            </div>
        </div>

        <div class="space-y-4 pt-6 border-t border-gray-800">
            <h2 class="text-lg font-semibold text-white">Subscribers & Authorized IPs</h2>
            <div class="bg-[#121722] border border-gray-800 rounded-2xl overflow-hidden shadow-xl">
                <table class="w-full text-left text-xs">
                    <thead class="bg-gray-900/60 text-gray-400 border-b border-gray-800">
                        <tr>
                            <th class="p-4">Customer</th>
                            <th class="p-4">Plan</th>
                            <th class="p-4">Authorized Home IP</th>
                            <th class="p-4">Status</th>
                            <th class="p-4">Expires At</th>
                        </tr>
                    </thead>
                    <tbody id="usersList" class="divide-y divide-gray-800/60 text-gray-300">
                        <tr>
                            <td colspan="5" class="p-6 text-center text-gray-500">No subscribers registered yet.</td>
                        </tr>
                    </tbody>
                </table>
            </div>
        </div>
    </div>

    <script>
        function checkAuth() {
            const pass = localStorage.getItem('admin_token');
            if (!pass) {
                const input = prompt('Enter Admin Password:');
                if (input) {
                    localStorage.setItem('admin_token', input);
                    loadData();
                }
            } else {
                loadData();
            }
        }

        async function loadData() {
            const pass = localStorage.getItem('admin_token');
            try {
                const res = await fetch('/api/admin/data', { headers: { 'Authorization': pass } });
                if (res.status === 401) {
                    localStorage.removeItem('admin_token');
                    alert('Invalid Admin Password!');
                    checkAuth();
                    return;
                }
                const data = await res.json();
                render(data);
            } catch(e) {
                console.error(e);
            }
        }

        function render(data) {
            document.getElementById('pendingCount').innerText = data.receipts.filter(r => r.status === 'PENDING').length;
            document.getElementById('activeCount').innerText = data.users.length;
            document.getElementById('ipCount').innerText = data.users.filter(u => u.ip).length;

            const recContainer = document.getElementById('receiptsList');
            const pending = data.receipts.filter(r => r.status === 'PENDING');
            if (pending.length === 0) {
                recContainer.innerHTML = '<div class="p-8 text-center bg-[#121722] border border-gray-800 rounded-2xl text-gray-500 text-sm col-span-full">No pending customer receipts right now.</div>';
            } else {
                recContainer.innerHTML = pending.map(r => \`
                    <div class="bg-[#121722] border border-gray-800 rounded-2xl p-5 space-y-4 shadow-xl">
                        <div class="flex justify-between items-start">
                            <div>
                                <span class="font-bold text-white text-base block">\${r.username}</span>
                                <span class="text-xs text-gray-400">\${r.phone || '-'}</span>
                            </div>
                            <span class="text-xs px-2.5 py-1 bg-blue-500/10 border border-blue-500/20 text-blue-400 rounded-lg font-medium">\${r.planName}</span>
                        </div>
                        <div class="p-3 bg-gray-900/80 rounded-xl space-y-1.5 text-xs font-mono">
                            <div class="flex justify-between text-gray-400"><span>Price:</span><span class="text-white font-bold">\${Number(r.price).toLocaleString()} T</span></div>
                            <div class="flex justify-between text-gray-400"><span>Ref / Trx:</span><span class="text-amber-400 font-bold">\${r.refNo}</span></div>
                            <div class="flex justify-between text-gray-400"><span>Card:</span><span class="text-gray-200">**** \${r.cardLast4}</span></div>
                        </div>
                        <div class="flex gap-2">
                            <button onclick="reviewReceipt('\${r.id}', 'APPROVE')" class="flex-1 py-2 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg text-xs font-semibold">Approve & Activate</button>
                            <button onclick="reviewReceipt('\${r.id}', 'REJECT')" class="px-3 py-2 bg-gray-800 hover:bg-rose-900/40 text-gray-400 hover:text-rose-400 rounded-lg text-xs">Reject</button>
                        </div>
                    </div>
                \`).join('');
            }

            const userContainer = document.getElementById('usersList');
            if (data.users.length === 0) {
                userContainer.innerHTML = '<tr><td colspan="5" class="p-6 text-center text-gray-500">No subscribers registered yet.</td></tr>';
            } else {
                userContainer.innerHTML = data.users.map(u => \`
                    <tr class="hover:bg-gray-900/30">
                        <td class="p-4 font-semibold text-white">\${u.username}</td>
                        <td class="p-4 text-gray-400">\${u.planName || '-'}</td>
                        <td class="p-4 font-mono text-blue-400">\${u.ip || 'Not synced'}</td>
                        <td class="p-4"><span class="px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 text-[10px] font-bold">ACTIVE</span></td>
                        <td class="p-4 text-gray-400">\${u.expiresAt ? new Date(u.expiresAt).toLocaleDateString() : '-'}</td>
                    </tr>
                \`).join('');
            }
        }

        async function reviewReceipt(id, action) {
            const pass = localStorage.getItem('admin_token');
            await fetch('/api/admin/receipt/' + id + '/review', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'Authorization': pass },
                body: JSON.stringify({ action })
            });
            loadData();
        }

        function logout() {
            localStorage.removeItem('admin_token');
            checkAuth();
        }

        checkAuth();
        setInterval(loadData, 10000);
    </script>
</body>
</html>`;

const server = http.createServer((req, res) => {
    const parsed = url.parse(req.url, true);
    
    // Serve Admin HTML Dashboard
    if (parsed.pathname === '/' || parsed.pathname === '/admin') {
        res.writeHead(200, { 'Content-Type': 'text/html' });
        res.end(htmlDashboard);
        return;
    }

    // Authenticate Admin API
    const authHeader = req.headers['authorization'];
    if (parsed.pathname.startsWith('/api/admin/')) {
        if (authHeader !== db.adminPassword) {
            res.writeHead(401, { 'Content-Type': 'application/json' });
            res.end(JSON.stringify({ error: 'Unauthorized' }));
            return;
        }

        if (parsed.pathname === '/api/admin/data' && req.method === 'GET') {
            res.writeHead(200, { 'Content-Type': 'application/json' });
            res.end(JSON.stringify(db));
            return;
        }

        if (parsed.pathname.startsWith('/api/admin/receipt/') && parsed.pathname.endsWith('/review') && req.method === 'POST') {
            let body = '';
            req.on('data', chunk => body += chunk);
            req.on('end', () => {
                const { action } = JSON.parse(body || '{}');
                const id = parsed.pathname.split('/')[4];
                const r = db.receipts.find(x => x.id === id);
                if (r) {
                    r.status = action === 'APPROVE' ? 'APPROVED' : 'REJECTED';
                    if (action === 'APPROVE') {
                        const days = r.durationDays || 30;
                        const exp = new Date(Date.now() + days * 24 * 60 * 60 * 1000);
                        let u = db.users.find(x => x.username === r.username);
                        if (!u) {
                            u = { username: r.username, phone: r.phone, planName: r.planName, ip: r.ip || null, expiresAt: exp };
                            db.users.push(u);
                        } else {
                            u.expiresAt = exp;
                            u.planName = r.planName;
                        }
                    }
                    saveDb();
                }
                res.writeHead(200, { 'Content-Type': 'application/json' });
                res.end(JSON.stringify({ success: true }));
            });
            return;
        }
    }

    // Public Customer Submission API
    if (parsed.pathname === '/api/submit-receipt' && req.method === 'POST') {
        let body = '';
        req.on('data', chunk => body += chunk);
        req.on('end', () => {
            const data = JSON.parse(body || '{}');
            const receipt = {
                id: crypto.randomBytes(4).toString('hex'),
                username: data.username,
                phone: data.phone,
                planName: data.planName,
                price: data.price,
                durationDays: data.durationDays || 30,
                refNo: data.refNo,
                cardLast4: data.cardLast4,
                ip: data.ip,
                status: 'PENDING',
                createdAt: new Date().toISOString()
            };
            db.receipts.unshift(receipt);
            saveDb();
            res.writeHead(200, { 'Content-Type': 'application/json' });
            res.end(JSON.stringify({ success: true, receipt }));
        });
        return;
    }

    res.writeHead(404, { 'Content-Type': 'text/plain' });
    res.end('Not Found');
});

server.listen(PORT, '0.0.0.0', () => {
    console.log(`[SmartDNS Admin Server] Running on http://0.0.0.0:${PORT}`);
});

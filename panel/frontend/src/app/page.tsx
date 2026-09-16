"use client";

import React, { useState, useEffect } from "react";
import { Shield, Zap, RefreshCw, Gamepad2, CheckCircle2, AlertCircle, Clock, CreditCard, ChevronRight, User } from "lucide-react";

export default function CustomerDashboard() {
  const [user, setUser] = useState<any>(null);
  const [currentIp, setCurrentIp] = useState<string>("");
  const [isSyncing, setIsSyncing] = useState<boolean>(false);
  const [syncStatus, setSyncStatus] = useState<string>("");
  const [plans, setPlans] = useState<any[]>([]);
  const [selectedPlan, setSelectedPlan] = useState<any>(null);
  const [trackingRef, setTrackingRef] = useState<string>("");
  const [cardDigits, setCardDigits] = useState<string>("");
  const [receiptMsg, setReceiptMsg] = useState<string>("");

  useEffect(() => {
    // Detect public IP
    fetch("/api/my-ip")
      .then((res) => res.json())
      .then((data) => setCurrentIp(data.ip))
      .catch(() => setCurrentIp("Failed to detect"));

    // Fetch plans
    fetch("/api/plans")
      .then((res) => res.json())
      .then((data) => {
        setPlans(data);
        if (data.length > 0) setSelectedPlan(data[0]);
      })
      .catch(console.error);

    // Fetch user profile if logged in
    const token = localStorage.getItem("token");
    if (token) {
      fetch("/api/customer/profile", {
        headers: { Authorization: `Bearer ${token}` },
      })
        .then((res) => res.json())
        .then((data) => setUser(data))
        .catch(console.error);
    }
  }, []);

  const handleSyncIp = async () => {
    setIsSyncing(true);
    setSyncStatus("");
    const token = localStorage.getItem("token");
    try {
      const res = await fetch("/api/customer/sync-ip", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ ip: currentIp }),
      });
      const data = await res.json();
      if (res.ok) {
        setSyncStatus("success");
      } else {
        setSyncStatus(data.error || "Failed to sync IP");
      }
    } catch (err) {
      setSyncStatus("Network error syncing IP");
    } finally {
      setIsSyncing(false);
    }
  };

  const handleSubmitReceipt = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedPlan) return;
    const token = localStorage.getItem("token");
    try {
      const res = await fetch("/api/customer/submit-receipt", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          planId: selectedPlan.id,
          trackingRef,
          cardLastDigits: cardDigits,
        }),
      });
      const data = await res.json();
      if (res.ok) {
        setReceiptMsg("Receipt submitted! Admin will verify and activate your pass shortly.");
        setTrackingRef("");
        setCardDigits("");
      } else {
        setReceiptMsg(data.error || "Submission failed");
      }
    } catch (err) {
      setReceiptMsg("Failed to submit receipt");
    }
  };

  const isSubActive = user?.subscription?.status === "ACTIVE";

  return (
    <div className="max-w-6xl mx-auto px-4 py-8">
      {/* Header */}
      <header className="flex flex-col md:flex-row justify-between items-start md:items-center pb-6 border-b border-gray-800 gap-4">
        <div className="flex items-center gap-3">
          <div className="p-2.5 bg-blue-600/20 border border-blue-500/30 rounded-xl text-blue-400">
            <Gamepad2 className="w-8 h-8" />
          </div>
          <div>
            <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2">
              SmartDNS Gaming Hub
              <span className="text-xs px-2.5 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                Live
              </span>
            </h1>
            <p className="text-sm text-gray-400">Low-Latency Console Anti-Sanction & Matchmaking Egress</p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          {user ? (
            <div className="flex items-center gap-2 bg-gray-900 border border-gray-800 px-3 py-1.5 rounded-lg text-sm">
              <User className="w-4 h-4 text-blue-400" />
              <span className="font-medium text-gray-200">{user.username}</span>
            </div>
          ) : (
            <a
              href="/login"
              className="bg-blue-600 hover:bg-blue-500 text-white font-medium px-4 py-2 rounded-lg text-sm transition"
            >
              Sign In / Register
            </a>
          )}
        </div>
      </header>

      {/* Main Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mt-8">
        {/* Left Column: 1-Click IP Sync & DNS Settings */}
        <div className="lg:col-span-2 space-y-6">
          {/* 1-Click IP Sync Card */}
          <div className="bg-[#121722] border border-gray-800 rounded-2xl p-6 relative overflow-hidden shadow-xl">
            <div className="absolute top-0 right-0 w-64 h-64 bg-blue-500/5 rounded-full blur-3xl pointer-events-none" />

            <div className="flex items-center justify-between pb-4 border-b border-gray-800/80">
              <div className="flex items-center gap-2.5">
                <Zap className="w-5 h-5 text-amber-400" />
                <h2 className="font-semibold text-lg text-white">1-Click Home IP Sync</h2>
              </div>
              <span className="text-xs text-gray-400">Dynamic IP Auto-Detection</span>
            </div>

            <div className="mt-6 flex flex-col md:flex-row items-start md:items-center justify-between gap-4 p-4 rounded-xl bg-gray-900/60 border border-gray-800">
              <div>
                <span className="text-xs text-gray-400 uppercase tracking-wider block">Your Current Public IP</span>
                <span className="text-2xl font-mono font-bold text-blue-400">{currentIp || "Detecting..."}</span>
              </div>

              <button
                onClick={handleSyncIp}
                disabled={isSyncing || !isSubActive}
                className={`flex items-center gap-2 px-5 py-3 rounded-xl font-medium text-sm transition shadow-lg ${
                  isSubActive
                    ? "bg-blue-600 hover:bg-blue-500 text-white shadow-blue-600/20"
                    : "bg-gray-800 text-gray-400 cursor-not-allowed"
                }`}
              >
                <RefreshCw className={`w-4 h-4 ${isSyncing ? "animate-spin" : ""}`} />
                {isSyncing ? "Syncing with DNS Server..." : "Sync / Authorize My IP"}
              </button>
            </div>

            {syncStatus === "success" && (
              <div className="mt-4 p-3 bg-emerald-500/10 border border-emerald-500/20 rounded-xl flex items-center gap-2 text-sm text-emerald-400">
                <CheckCircle2 className="w-4 h-4" />
                Your IP ({currentIp}) has been authorized on the DNS server! Consoles are ready to play.
              </div>
            )}

            {syncStatus && syncStatus !== "success" && (
              <div className="mt-4 p-3 bg-rose-500/10 border border-rose-500/20 rounded-xl flex items-center gap-2 text-sm text-rose-400">
                <AlertCircle className="w-4 h-4" />
                {syncStatus}
              </div>
            )}

            {!isSubActive && (
              <div className="mt-4 p-3 bg-amber-500/10 border border-amber-500/20 rounded-xl flex items-center gap-2 text-xs text-amber-300">
                <AlertCircle className="w-4 h-4 text-amber-400 flex-shrink-0" />
                Please purchase or activate a gaming pass below to authorize your IP for the DNS proxy.
              </div>
            )}
          </div>

          {/* Console Setup Information Card */}
          <div className="bg-[#121722] border border-gray-800 rounded-2xl p-6 shadow-xl">
            <h2 className="font-semibold text-lg text-white mb-4 flex items-center gap-2">
              <Shield className="w-5 h-5 text-blue-400" />
              Console Network Setup
            </h2>

            <p className="text-sm text-gray-400 mb-6">
              Enter these DNS addresses manually into your PlayStation 5, Xbox Series X/S, or Nintendo Switch network settings:
            </p>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="p-4 rounded-xl bg-gray-900/80 border border-gray-800">
                <span className="text-xs text-gray-400 uppercase tracking-wider block">Primary DNS (Iran Server)</span>
                <span className="text-xl font-mono font-bold text-emerald-400">77.104.92.169</span>
              </div>
              <div className="p-4 rounded-xl bg-gray-900/80 border border-gray-800">
                <span className="text-xs text-gray-400 uppercase tracking-wider block">Secondary DNS (Backup)</span>
                <span className="text-xl font-mono font-bold text-gray-300">1.1.1.1</span>
              </div>
            </div>

            <div className="mt-6 border-t border-gray-800/80 pt-4 text-xs text-gray-500 space-y-1">
              <p>✔ Full speed game downloads (CDN files download directly at full ISP speed without proxying).</p>
              <p>✔ Only blocked authentication, lobbies, and game stores are routed through the European bridge.</p>
            </div>
          </div>
        </div>

        {/* Right Column: Active Pass & Subscription Purchase */}
        <div className="space-y-6">
          {/* Active Subscription Status */}
          <div className="bg-[#121722] border border-gray-800 rounded-2xl p-6 shadow-xl">
            <h3 className="font-semibold text-base text-white mb-4 flex items-center gap-2">
              <Clock className="w-4 h-4 text-purple-400" />
              Active Subscription
            </h3>

            {isSubActive ? (
              <div className="space-y-3">
                <div className="p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/20">
                  <div className="flex justify-between items-center mb-1">
                    <span className="text-xs text-emerald-300 uppercase font-semibold">Status</span>
                    <span className="text-xs px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-300 font-bold">
                      ACTIVE
                    </span>
                  </div>
                  <span className="text-lg font-bold text-white block">
                    {user?.subscription?.plan?.name || "Gaming Pass"}
                  </span>
                  <span className="text-xs text-gray-400 mt-1 block">
                    Expires: {new Date(user.subscription.expiresAt).toLocaleDateString()}
                  </span>
                </div>
              </div>
            ) : (
              <div className="p-4 rounded-xl bg-gray-900/80 border border-gray-800 text-center">
                <span className="text-sm font-medium text-gray-300 block mb-1">No Active Pass</span>
                <span className="text-xs text-gray-500 block">Select a plan below to activate your account.</span>
              </div>
            )}
          </div>

          {/* Plan Purchase & Receipt Submission */}
          <div className="bg-[#121722] border border-gray-800 rounded-2xl p-6 shadow-xl">
            <h3 className="font-semibold text-base text-white mb-4 flex items-center gap-2">
              <CreditCard className="w-4 h-4 text-blue-400" />
              Upgrade / Renew Pass
            </h3>

            <div className="space-y-3 mb-6">
              {plans.map((p) => (
                <div
                  key={p.id}
                  onClick={() => setSelectedPlan(p)}
                  className={`p-3.5 rounded-xl border cursor-pointer transition flex items-center justify-between ${
                    selectedPlan?.id === p.id
                      ? "bg-blue-600/10 border-blue-500/40 text-white"
                      : "bg-gray-900/60 border-gray-800 text-gray-400 hover:border-gray-700"
                  }`}
                >
                  <div>
                    <span className="font-medium text-sm block text-gray-200">{p.name}</span>
                    <span className="text-xs text-gray-400">{p.description}</span>
                  </div>
                  <span className="font-bold text-blue-400 text-sm">
                    {Number(p.priceToman).toLocaleString()} T
                  </span>
                </div>
              ))}
            </div>

            {/* Payment Details */}
            <div className="p-3.5 rounded-xl bg-gray-900/90 border border-gray-800 mb-6 text-xs text-gray-300 space-y-1 font-mono">
              <span className="text-gray-500 block uppercase font-sans">Payment Details (Card to Card)</span>
              <div>Card: <span className="text-white font-bold">6037-9918-XXXX-XXXX</span></div>
              <div>Holder: <span className="text-white">SmartDNS Gaming</span></div>
            </div>

            {/* Receipt Form */}
            <form onSubmit={handleSubmitReceipt} className="space-y-3">
              <div>
                <label className="text-xs text-gray-400 block mb-1">Tracking Number / Reference</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. 192847192"
                  value={trackingRef}
                  onChange={(e) => setTrackingRef(e.target.value)}
                  className="w-full px-3 py-2 bg-gray-900 border border-gray-800 rounded-lg text-sm text-gray-200 focus:outline-none focus:border-blue-500"
                />
              </div>

              <div>
                <label className="text-xs text-gray-400 block mb-1">Last 4 Digits of Your Card</label>
                <input
                  type="text"
                  maxLength={4}
                  placeholder="e.g. 4821"
                  value={cardDigits}
                  onChange={(e) => setCardDigits(e.target.value)}
                  className="w-full px-3 py-2 bg-gray-900 border border-gray-800 rounded-lg text-sm text-gray-200 focus:outline-none focus:border-blue-500"
                />
              </div>

              <button
                type="submit"
                className="w-full py-2.5 bg-blue-600 hover:bg-blue-500 text-white font-medium rounded-lg text-sm transition shadow-lg shadow-blue-600/20"
              >
                Submit Receipt for Verification
              </button>

              {receiptMsg && (
                <div className="p-2.5 bg-blue-500/10 border border-blue-500/20 rounded-lg text-xs text-blue-300">
                  {receiptMsg}
                </div>
              )}
            </form>
          </div>
        </div>
      </div>
    </div>
  );
}

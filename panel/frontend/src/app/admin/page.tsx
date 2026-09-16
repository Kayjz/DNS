"use client";

import React, { useState, useEffect } from "react";
import { ShieldCheck, Users, CreditCard, CheckCircle, XCircle, Clock, Search, AlertCircle, RefreshCw } from "lucide-react";

export default function AdminPortal() {
  const [users, setUsers] = useState<any[]>([]);
  const [receipts, setReceipts] = useState<any[]>([]);
  const [activeTab, setActiveTab] = useState<"receipts" | "users">("receipts");
  const [search, setSearch] = useState<string>("");
  const [actionLoading, setActionLoading] = useState<string | null>(null);

  const fetchAdminData = () => {
    const token = localStorage.getItem("token");
    if (!token) return;

    fetch("/api/admin/receipts", {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((res) => res.json())
      .then((data) => setReceipts(data))
      .catch(console.error);

    fetch("/api/admin/users", {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((res) => res.json())
      .then((data) => setUsers(data))
      .catch(console.error);
  };

  useEffect(() => {
    fetchAdminData();
  }, []);

  const handleReviewReceipt = async (id: string, action: "APPROVE" | "REJECT") => {
    setActionLoading(id);
    const token = localStorage.getItem("token");
    try {
      const res = await fetch(`/api/admin/receipts/${id}/review`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ action }),
      });
      if (res.ok) {
        fetchAdminData();
      }
    } catch (err) {
      console.error(err);
    } finally {
      setActionLoading(null);
    }
  };

  const pendingReceipts = receipts.filter((r) => r.status === "PENDING");
  const reviewedReceipts = receipts.filter((r) => r.status !== "PENDING");

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      {/* Header */}
      <div className="flex justify-between items-center pb-6 border-b border-gray-800">
        <div className="flex items-center gap-3">
          <div className="p-2.5 bg-purple-600/20 border border-purple-500/30 rounded-xl text-purple-400">
            <ShieldCheck className="w-8 h-8" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-white">SmartDNS Master Admin Portal</h1>
            <p className="text-sm text-gray-400">Manage Customers, Approve Payment Receipts & Whitelist</p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={fetchAdminData}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-gray-900 border border-gray-800 rounded-lg text-xs text-gray-300 hover:text-white"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            Refresh
          </button>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex items-center gap-4 mt-8 border-b border-gray-800">
        <button
          onClick={() => setActiveTab("receipts")}
          className={`pb-3 text-sm font-medium transition flex items-center gap-2 border-b-2 ${
            activeTab === "receipts"
              ? "border-blue-500 text-blue-400"
              : "border-transparent text-gray-400 hover:text-gray-200"
          }`}
        >
          <CreditCard className="w-4 h-4" />
          Payment Receipts
          {pendingReceipts.length > 0 && (
            <span className="px-2 py-0.5 rounded-full bg-amber-500/20 text-amber-300 text-xs font-bold">
              {pendingReceipts.length}
            </span>
          )}
        </button>

        <button
          onClick={() => setActiveTab("users")}
          className={`pb-3 text-sm font-medium transition flex items-center gap-2 border-b-2 ${
            activeTab === "users"
              ? "border-blue-500 text-blue-400"
              : "border-transparent text-gray-400 hover:text-gray-200"
          }`}
        >
          <Users className="w-4 h-4" />
          Subscribers & Clients ({users.length})
        </button>
      </div>

      {/* TAB 1: RECEIPTS */}
      {activeTab === "receipts" && (
        <div className="mt-6 space-y-6">
          <h2 className="text-lg font-semibold text-white flex items-center gap-2">
            <Clock className="w-5 h-5 text-amber-400" />
            Pending Verification ({pendingReceipts.length})
          </h2>

          {pendingReceipts.length === 0 ? (
            <div className="p-8 text-center bg-[#121722] border border-gray-800 rounded-2xl text-gray-500 text-sm">
              No pending payment receipts right now.
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {pendingReceipts.map((r) => (
                <div key={r.id} className="bg-[#121722] border border-gray-800 rounded-2xl p-5 space-y-4 shadow-xl">
                  <div className="flex justify-between items-start">
                    <div>
                      <span className="font-bold text-white text-base block">{r.user?.username}</span>
                      <span className="text-xs text-gray-400">{r.user?.phoneOrEmail}</span>
                    </div>
                    <span className="text-xs px-2.5 py-1 bg-blue-500/10 border border-blue-500/20 text-blue-400 rounded-lg font-medium">
                      {r.plan?.name}
                    </span>
                  </div>

                  <div className="p-3 bg-gray-900/80 rounded-xl space-y-1.5 text-xs font-mono">
                    <div className="flex justify-between text-gray-400">
                      <span>Price:</span>
                      <span className="text-white font-bold">{Number(r.plan?.priceToman).toLocaleString()} Toman</span>
                    </div>
                    <div className="flex justify-between text-gray-400">
                      <span>Ref / Trx:</span>
                      <span className="text-amber-400 font-bold">{r.trackingRef || "N/A"}</span>
                    </div>
                    <div className="flex justify-between text-gray-400">
                      <span>Card Digits:</span>
                      <span className="text-gray-200">**** {r.cardLastDigits || "N/A"}</span>
                    </div>
                  </div>

                  <div className="flex items-center gap-2 pt-2 border-t border-gray-800/80">
                    <button
                      disabled={actionLoading === r.id}
                      onClick={() => handleReviewReceipt(r.id, "APPROVE")}
                      className="flex-1 py-2 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg text-xs font-semibold flex items-center justify-center gap-1.5 transition"
                    >
                      <CheckCircle className="w-3.5 h-3.5" />
                      Approve & Activate
                    </button>
                    <button
                      disabled={actionLoading === r.id}
                      onClick={() => handleReviewReceipt(r.id, "REJECT")}
                      className="py-2 px-3 bg-gray-800 hover:bg-rose-900/40 text-gray-400 hover:text-rose-400 rounded-lg text-xs font-medium transition"
                    >
                      <XCircle className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Past History */}
          {reviewedReceipts.length > 0 && (
            <div className="mt-8">
              <h3 className="text-sm font-semibold text-gray-400 mb-4">Verification History</h3>
              <div className="bg-[#121722] border border-gray-800 rounded-2xl overflow-hidden">
                <table className="w-full text-left text-xs">
                  <thead className="bg-gray-900/60 text-gray-400 border-b border-gray-800">
                    <tr>
                      <th className="p-3.5">User</th>
                      <th className="p-3.5">Plan</th>
                      <th className="p-3.5">Ref No</th>
                      <th className="p-3.5">Status</th>
                      <th className="p-3.5">Date</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-800/60 text-gray-300">
                    {reviewedReceipts.map((r) => (
                      <tr key={r.id}>
                        <td className="p-3.5 font-medium text-white">{r.user?.username}</td>
                        <td className="p-3.5">{r.plan?.name}</td>
                        <td className="p-3.5 font-mono">{r.trackingRef || "-"}</td>
                        <td className="p-3.5">
                          <span
                            className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                              r.status === "APPROVED"
                                ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                                : "bg-rose-500/10 text-rose-400 border border-rose-500/20"
                            }`}
                          >
                            {r.status}
                          </span>
                        </td>
                        <td className="p-3.5 text-gray-500">{new Date(r.createdAt).toLocaleDateString()}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      )}

      {/* TAB 2: SUBSCRIBERS */}
      {activeTab === "users" && (
        <div className="mt-6 space-y-4">
          <div className="bg-[#121722] border border-gray-800 rounded-2xl overflow-hidden shadow-xl">
            <table className="w-full text-left text-xs">
              <thead className="bg-gray-900/60 text-gray-400 border-b border-gray-800">
                <tr>
                  <th className="p-4">Customer</th>
                  <th className="p-4">Contact</th>
                  <th className="p-4">Role</th>
                  <th className="p-4">Status</th>
                  <th className="p-4">Active Home IP</th>
                  <th className="p-4">Subscription Expires</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-800/60 text-gray-300">
                {users.map((u) => {
                  const sub = u.subscription;
                  const isExpired = sub ? new Date(sub.expiresAt) < new Date() : true;
                  return (
                    <tr key={u.id} className="hover:bg-gray-900/30 transition">
                      <td className="p-4 font-semibold text-white">{u.username}</td>
                      <td className="p-4 text-gray-400">{u.phoneOrEmail}</td>
                      <td className="p-4">
                        <span className="px-2 py-0.5 rounded bg-gray-800 text-gray-300 font-mono text-[10px]">
                          {u.role}
                        </span>
                      </td>
                      <td className="p-4">
                        {sub?.status === "ACTIVE" && !isExpired ? (
                          <span className="px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-bold text-[10px]">
                            ACTIVE
                          </span>
                        ) : (
                          <span className="px-2 py-0.5 rounded bg-gray-800 text-gray-500 font-medium text-[10px]">
                            EXPIRED / NONE
                          </span>
                        )}
                      </td>
                      <td className="p-4 font-mono text-blue-400">
                        {sub?.activeClientIp || <span className="text-gray-600">Not synced</span>}
                      </td>
                      <td className="p-4 text-gray-400">
                        {sub?.expiresAt ? new Date(sub.expiresAt).toLocaleDateString() : "-"}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}

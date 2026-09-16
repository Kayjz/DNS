"use client";

import React, { useState } from "react";
import { Gamepad2, Lock, User, Phone, ArrowRight } from "lucide-react";

export default function LoginPage() {
  const [isRegister, setIsRegister] = useState(false);
  const [username, setUsername] = useState("");
  const [phoneOrEmail, setPhoneOrEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);

    const endpoint = isRegister ? "/api/auth/register" : "/api/auth/login";
    const payload = isRegister
      ? { username, phoneOrEmail, password }
      : { loginIdentifier: username, password };

    try {
      const res = await fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await res.json();

      if (res.ok) {
        localStorage.setItem("token", data.token);
        if (data.user.role === "ADMIN") {
          window.location.href = "/admin";
        } else {
          window.location.href = "/";
        }
      } else {
        setError(data.error || "Authentication failed");
      }
    } catch (err) {
      setError("Network error connecting to server");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center px-4 py-12">
      <div className="max-w-md w-full bg-[#121722] border border-gray-800 rounded-3xl p-8 shadow-2xl relative overflow-hidden">
        <div className="absolute -top-12 -right-12 w-48 h-48 bg-blue-500/10 rounded-full blur-3xl pointer-events-none" />

        <div className="text-center mb-8">
          <div className="inline-flex p-3 bg-blue-600/20 border border-blue-500/30 rounded-2xl text-blue-400 mb-3">
            <Gamepad2 className="w-8 h-8" />
          </div>
          <h1 className="text-2xl font-bold text-white tracking-tight">
            {isRegister ? "Create Gamer Account" : "Welcome Back"}
          </h1>
          <p className="text-xs text-gray-400 mt-1">
            {isRegister
              ? "Register to get your dedicated SmartDNS console pass"
              : "Sign in to manage your active console IP and subscription"}
          </p>
        </div>

        {error && (
          <div className="mb-4 p-3 bg-rose-500/10 border border-rose-500/20 rounded-xl text-xs text-rose-400">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-xs text-gray-400 mb-1">Username</label>
            <div className="relative">
              <User className="w-4 h-4 text-gray-500 absolute left-3 top-3" />
              <input
                type="text"
                required
                placeholder="e.g. AlborzGamer"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                className="w-full pl-9 pr-3 py-2.5 bg-gray-900 border border-gray-800 rounded-xl text-sm text-gray-200 focus:outline-none focus:border-blue-500"
              />
            </div>
          </div>

          {isRegister && (
            <div>
              <label className="block text-xs text-gray-400 mb-1">Phone Number or Email</label>
              <div className="relative">
                <Phone className="w-4 h-4 text-gray-500 absolute left-3 top-3" />
                <input
                  type="text"
                  required
                  placeholder="0912... or email@domain.com"
                  value={phoneOrEmail}
                  onChange={(e) => setPhoneOrEmail(e.target.value)}
                  className="w-full pl-9 pr-3 py-2.5 bg-gray-900 border border-gray-800 rounded-xl text-sm text-gray-200 focus:outline-none focus:border-blue-500"
                />
              </div>
            </div>
          )}

          <div>
            <label className="block text-xs text-gray-400 mb-1">Password</label>
            <div className="relative">
              <Lock className="w-4 h-4 text-gray-500 absolute left-3 top-3" />
              <input
                type="password"
                required
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full pl-9 pr-3 py-2.5 bg-gray-900 border border-gray-800 rounded-xl text-sm text-gray-200 focus:outline-none focus:border-blue-500"
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full py-3 bg-blue-600 hover:bg-blue-500 text-white font-medium rounded-xl text-sm transition shadow-lg shadow-blue-600/20 flex items-center justify-center gap-2 mt-6"
          >
            {loading ? "Processing..." : isRegister ? "Create Account" : "Sign In"}
            <ArrowRight className="w-4 h-4" />
          </button>
        </form>

        <div className="mt-6 text-center">
          <button
            onClick={() => {
              setIsRegister(!isRegister);
              setError("");
            }}
            className="text-xs text-blue-400 hover:text-blue-300 font-medium transition"
          >
            {isRegister
              ? "Already have an account? Sign in"
              : "Don't have an account? Register now"}
          </button>
        </div>
      </div>
    </div>
  );
}

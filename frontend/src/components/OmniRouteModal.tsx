"use client";

import React, { useState, useEffect } from "react";
import { getOmniRouteConfig, setOmniRouteConfig, testOmniRouteConnection } from "../lib/api";

interface OmniRouteModalProps {
  isOpen: boolean;
  onClose: () => void;
  onConfigSaved?: () => void;
}

export function OmniRouteModal({ isOpen, onClose, onConfigSaved }: OmniRouteModalProps) {
  const [apiKey, setApiKey] = useState("");
  const [baseUrl, setBaseUrl] = useState("http://localhost:20128/v1");
  const [model, setModel] = useState("google/gemini-2.0-flash-001");
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<{ success?: boolean; msg?: string } | null>(null);

  useEffect(() => {
    if (isOpen) {
      const cfg = getOmniRouteConfig();
      setApiKey(cfg.apiKey);
      setBaseUrl(cfg.baseUrl);
      setModel(cfg.model);
      setTestResult(null);
    }
  }, [isOpen]);

  if (!isOpen) return null;

  const handleTest = async () => {
    if (!apiKey.trim()) {
      setTestResult({ success: false, msg: "Please enter an OmniRoute API key first." });
      return;
    }
    setTesting(true);
    setTestResult(null);
    try {
      const res = await testOmniRouteConnection({ apiKey, baseUrl, model });
      if (res.success) {
        setTestResult({
          success: true,
          msg: `Connected successfully to OmniRoute (${model})!`,
        });
      } else {
        setTestResult({
          success: false,
          msg: `Connection failed: ${res.error || "Unknown error"}`,
        });
      }
    } catch (e: any) {
      setTestResult({
        success: false,
        msg: `Connection error: ${e.message || "Failed to reach OmniRoute"}`,
      });
    } finally {
      setTesting(false);
    }
  };

  const handleSave = () => {
    setOmniRouteConfig({ apiKey, baseUrl, model });
    if (onConfigSaved) onConfigSaved();
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md animate-fade-in">
      <div className="relative w-full max-w-xl p-6 border border-purple-500/30 rounded-2xl bg-[#0F0F17] shadow-2xl shadow-purple-900/20 text-white">
        {/* Close Button */}
        <button
          onClick={onClose}
          className="absolute top-4 right-4 p-2 text-zinc-400 hover:text-white transition"
        >
          ✕
        </button>

        {/* Modal Header */}
        <div className="flex items-center gap-3 mb-2">
          <div className="flex items-center justify-center w-10 h-10 rounded-xl bg-purple-600/20 text-purple-400 border border-purple-500/30 font-bold text-lg">
            ⚡
          </div>
          <div>
            <h3 className="text-xl font-bold tracking-tight text-white flex items-center gap-2">
              OmniRoute AI Brain Settings
              <span className="text-xs px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-medium">
                BYOK Enabled
              </span>
            </h3>
            <p className="text-xs text-zinc-400">
              Paste your personal OmniRoute or OpenAI-compatible key for unlimited viral clipping.
            </p>
          </div>
        </div>

        {/* Form Fields */}
        <div className="mt-5 space-y-4">
          <div>
            <label className="block text-xs font-semibold text-zinc-300 uppercase tracking-wider mb-1.5">
              OmniRoute API Key
            </label>
            <input
              type="password"
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              placeholder="sk-omni-... or any OpenAI-compatible key"
              className="w-full px-3.5 py-2.5 rounded-lg bg-zinc-900/90 border border-zinc-800 text-sm text-zinc-100 placeholder-zinc-500 focus:outline-none focus:border-purple-500 focus:ring-1 focus:ring-purple-500 transition font-mono"
            />
            <p className="text-[11px] text-zinc-500 mt-1">
              Stored strictly in your local browser storage. Never sent to any external tracking server.
            </p>
          </div>

          <div>
            <label className="block text-xs font-semibold text-zinc-300 uppercase tracking-wider mb-1.5">
              AI Gateway Endpoint
            </label>
            <input
              type="text"
              value={baseUrl}
              onChange={(e) => setBaseUrl(e.target.value)}
              placeholder="http://localhost:20128/v1"
              className="w-full px-3.5 py-2.5 rounded-lg bg-zinc-900/90 border border-zinc-800 text-sm text-zinc-100 placeholder-zinc-500 focus:outline-none focus:border-purple-500 transition font-mono"
            />
            <div className="flex gap-2 mt-2">
              <button
                type="button"
                onClick={() => setBaseUrl("http://localhost:20128/v1")}
                className="text-[11px] px-2 py-1 rounded bg-zinc-800/80 hover:bg-zinc-700 text-zinc-300 border border-zinc-700/50 transition font-mono"
              >
                OmniRoute (:20128)
              </button>
              <button
                type="button"
                onClick={() => setBaseUrl("http://localhost:3001/v1")}
                className="text-[11px] px-2 py-1 rounded bg-zinc-800/80 hover:bg-zinc-700 text-zinc-300 border border-zinc-700/50 transition font-mono"
              >
                FreeLLMAPI (:3001)
              </button>
              <button
                type="button"
                onClick={() => setBaseUrl("https://openrouter.ai/api/v1")}
                className="text-[11px] px-2 py-1 rounded bg-zinc-800/80 hover:bg-zinc-700 text-zinc-300 border border-zinc-700/50 transition font-mono"
              >
                OpenRouter (Cloud)
              </button>
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-zinc-300 uppercase tracking-wider mb-1.5">
              AI Routing Model
            </label>
            <input
              type="text"
              value={model}
              onChange={(e) => setModel(e.target.value)}
              placeholder="google/gemini-2.0-flash-001"
              className="w-full px-3.5 py-2.5 rounded-lg bg-zinc-900/90 border border-zinc-800 text-sm text-zinc-100 placeholder-zinc-500 focus:outline-none focus:border-purple-500 transition font-mono"
            />
            <div className="flex gap-2 mt-2">
              <button
                type="button"
                onClick={() => setModel("google/gemini-2.0-flash-001")}
                className="text-[11px] px-2 py-1 rounded bg-zinc-800/80 hover:bg-zinc-700 text-zinc-300 border border-zinc-700/50 transition"
              >
                Gemini 2.0 Flash (Free)
              </button>
              <button
                type="button"
                onClick={() => setModel("deepseek/deepseek-chat")}
                className="text-[11px] px-2 py-1 rounded bg-zinc-800/80 hover:bg-zinc-700 text-zinc-300 border border-zinc-700/50 transition"
              >
                DeepSeek-V3
              </button>
              <button
                type="button"
                onClick={() => setModel("anthropic/claude-3-5-haiku")}
                className="text-[11px] px-2 py-1 rounded bg-zinc-800/80 hover:bg-zinc-700 text-zinc-300 border border-zinc-700/50 transition"
              >
                Claude 3.5 Haiku
              </button>
            </div>
          </div>
        </div>

        {/* Test Result Feedback */}
        {testResult && (
          <div
            className={`mt-4 p-3 rounded-lg text-xs flex items-center gap-2 border ${
              testResult.success
                ? "bg-emerald-950/40 text-emerald-300 border-emerald-500/30"
                : "bg-red-950/40 text-red-300 border-red-500/30"
            }`}
          >
            <span>{testResult.success ? "🟢" : "🔴"}</span>
            <span>{testResult.msg}</span>
          </div>
        )}

        {/* Modal Actions */}
        <div className="flex items-center justify-between gap-3 mt-6 pt-4 border-t border-zinc-800/80">
          <button
            type="button"
            onClick={handleTest}
            disabled={testing}
            className="px-4 py-2 rounded-lg bg-zinc-800 hover:bg-zinc-700 text-zinc-200 text-xs font-semibold border border-zinc-700 transition disabled:opacity-50"
          >
            {testing ? "Testing..." : "⚡ Test Connection"}
          </button>

          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 rounded-lg text-zinc-400 hover:text-white text-xs font-medium transition"
            >
              Cancel
            </button>
            <button
              type="button"
              onClick={handleSave}
              className="px-5 py-2 rounded-lg bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white text-xs font-semibold shadow-lg shadow-purple-600/30 transition"
            >
              Save & Activate Brain
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

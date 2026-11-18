"use client";

import React, { useState, useEffect } from "react";
import {
  getAIProviderConfig,
  setAIProviderConfig,
  testAIProviderConnection,
  PROVIDER_PRESETS,
  AIProviderConfig,
} from "../lib/api";
import { Sparkles, Key, CheckCircle2, AlertCircle, ExternalLink, Zap } from "lucide-react";

interface OmniRouteModalProps {
  isOpen: boolean;
  onClose: () => void;
  onConfigSaved?: () => void;
}

export function OmniRouteModal({ isOpen, onClose, onConfigSaved }: OmniRouteModalProps) {
  const [provider, setProvider] = useState<string>("gemini");
  const [apiKey, setApiKey] = useState<string>("");
  const [baseUrl, setBaseUrl] = useState<string>("");
  const [model, setModel] = useState<string>("");
  const [testing, setTesting] = useState<boolean>(false);
  const [testResult, setTestResult] = useState<{ success?: boolean; msg?: string } | null>(null);

  useEffect(() => {
    if (isOpen) {
      const cfg = getAIProviderConfig();
      setProvider(cfg.provider || "gemini");
      setApiKey(cfg.apiKey || "");
      setBaseUrl(cfg.baseUrl || PROVIDER_PRESETS.gemini.baseUrl);
      setModel(cfg.model || PROVIDER_PRESETS.gemini.defaultModel);
      setTestResult(null);
    }
  }, [isOpen]);

  if (!isOpen) return null;

  const handleSelectProvider = (key: string) => {
    setProvider(key);
    const preset = PROVIDER_PRESETS[key];
    if (preset) {
      setBaseUrl(preset.baseUrl);
      setModel(preset.defaultModel);
      // If user had empty key or changed provider, clear test result
      setTestResult(null);
    }
  };

  const handleTest = async () => {
    const isOllama = provider === "ollama" || baseUrl.includes("11434");
    if (!apiKey.trim() && !isOllama) {
      setTestResult({ success: false, msg: `Please enter your ${PROVIDER_PRESETS[provider]?.name || "API"} key first.` });
      return;
    }

    setTesting(true);
    setTestResult(null);
    try {
      const res = await testAIProviderConnection({ provider, apiKey, baseUrl, model });
      if (res.success) {
        setTestResult({
          success: true,
          msg: `Connected successfully to ${PROVIDER_PRESETS[provider]?.name || provider} (${model})!`,
        });
      } else {
        setTestResult({
          success: false,
          msg: `Connection failed: ${res.error || "Unable to reach endpoint"}`,
        });
      }
    } catch (e: any) {
      setTestResult({
        success: false,
        msg: `Connection error: ${e.message || "Failed to reach endpoint"}`,
      });
    } finally {
      setTesting(false);
    }
  };

  const handleSave = () => {
    setAIProviderConfig({ provider, apiKey, baseUrl, model });
    if (onConfigSaved) onConfigSaved();
    onClose();
  };

  const currentPreset = PROVIDER_PRESETS[provider] || PROVIDER_PRESETS.custom;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md animate-fade-in">
      <div className="relative w-full max-w-2xl p-6 md:p-8 border border-purple-500/30 rounded-2xl bg-[#0F0F17] shadow-2xl shadow-purple-900/25 text-white max-h-[92vh] overflow-y-auto">
        {/* Close Button */}
        <button
          onClick={onClose}
          className="absolute top-5 right-5 p-2 text-zinc-400 hover:text-white transition rounded-lg hover:bg-zinc-800"
        >
          ✕
        </button>

        {/* Modal Header */}
        <div className="flex items-center gap-3 mb-4">
          <div className="flex items-center justify-center w-11 h-11 rounded-xl bg-purple-600/20 text-purple-400 border border-purple-500/30 font-bold text-lg">
            <Zap className="w-5 h-5 text-purple-400" />
          </div>
          <div>
            <h3 className="text-xl font-bold tracking-tight text-white flex items-center gap-2">
              Connect Any AI Provider
              <span className="text-xs px-2.5 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 font-medium">
                Universal BYOK
              </span>
            </h3>
            <p className="text-xs text-zinc-400 mt-0.5">
              Select your AI brain. Connect free developer tiers, local self-hosted routers, or direct API keys.
            </p>
          </div>
        </div>

        {/* Provider Selection Grid */}
        <div className="mt-4 space-y-2">
          <label className="block text-xs font-semibold text-zinc-300 uppercase tracking-wider">
            1. Select Your AI Provider
          </label>
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
            {Object.entries(PROVIDER_PRESETS).map(([k, p]) => (
              <button
                key={k}
                type="button"
                onClick={() => handleSelectProvider(k)}
                className={`p-2.5 rounded-xl border text-left transition flex flex-col justify-between ${
                  provider === k
                    ? "bg-purple-600/20 border-purple-500 text-white shadow-md shadow-purple-600/15"
                    : "bg-zinc-900/80 border-zinc-800 text-zinc-400 hover:border-zinc-700 hover:text-zinc-200"
                }`}
              >
                <div className="flex items-center justify-between w-full">
                  <span className="font-bold text-xs text-zinc-100 truncate">{p.name.split(" ")[0]}</span>
                  <span className="text-[9px] px-1.5 py-0.5 rounded bg-zinc-800 text-purple-300 font-mono">
                    {p.tag.split(" ")[0]}
                  </span>
                </div>
                <span className="text-[11px] text-zinc-400 mt-1 truncate">
                  {p.name.replace(/^[^\(]+\(/, "(")}
                </span>
              </button>
            ))}
          </div>
        </div>

        {/* API Key Input */}
        <div className="mt-5 space-y-4">
          <div>
            <div className="flex items-center justify-between mb-1.5">
              <label className="block text-xs font-semibold text-zinc-300 uppercase tracking-wider">
                2. Enter API Key
              </label>
              {currentPreset.keyUrl && (
                <a
                  href={currentPreset.keyUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-xs text-purple-400 hover:text-purple-300 flex items-center gap-1 transition"
                >
                  <span>Get Free Key</span>
                  <ExternalLink className="w-3 h-3" />
                </a>
              )}
            </div>
            <input
              type="password"
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              placeholder={currentPreset.keyHint || "Paste your API key here"}
              className="w-full px-3.5 py-2.5 rounded-xl bg-zinc-900 border border-zinc-800 text-sm text-zinc-100 placeholder-zinc-500 focus:outline-none focus:border-purple-500 transition font-mono"
            />
            <p className="text-[11px] text-zinc-500 mt-1">
              Your key stays 100% private in your browser storage. It is never logged or stored on any external server.
            </p>
          </div>

          {/* Endpoint URL & Model Details */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-semibold text-zinc-300 uppercase tracking-wider mb-1.5">
                API Base URL
              </label>
              <input
                type="text"
                value={baseUrl}
                onChange={(e) => setBaseUrl(e.target.value)}
                placeholder="https://..."
                className="w-full px-3 py-2 rounded-lg bg-zinc-900/90 border border-zinc-800 text-xs text-zinc-200 placeholder-zinc-500 focus:outline-none focus:border-purple-500 transition font-mono"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-zinc-300 uppercase tracking-wider mb-1.5">
                Target Model
              </label>
              <input
                type="text"
                value={model}
                onChange={(e) => setModel(e.target.value)}
                placeholder="Model name"
                className="w-full px-3 py-2 rounded-lg bg-zinc-900/90 border border-zinc-800 text-xs text-zinc-200 placeholder-zinc-500 focus:outline-none focus:border-purple-500 transition font-mono"
              />
            </div>
          </div>
        </div>

        {/* Live Test Feedback Banner */}
        {testResult && (
          <div
            className={`mt-4 p-3.5 rounded-xl text-xs flex items-center gap-2.5 border ${
              testResult.success
                ? "bg-emerald-950/40 text-emerald-300 border-emerald-500/40"
                : "bg-red-950/40 text-red-300 border-red-500/40"
            }`}
          >
            {testResult.success ? (
              <CheckCircle2 className="w-4 h-4 text-emerald-400 flex-shrink-0" />
            ) : (
              <AlertCircle className="w-4 h-4 text-red-400 flex-shrink-0" />
            )}
            <span className="font-medium">{testResult.msg}</span>
          </div>
        )}

        {/* Action Buttons */}
        <div className="flex items-center justify-between gap-3 mt-6 pt-4 border-t border-zinc-800/80">
          <button
            type="button"
            onClick={handleTest}
            disabled={testing}
            className="px-4 py-2 rounded-xl bg-zinc-800 hover:bg-zinc-700 text-zinc-200 text-xs font-semibold border border-zinc-700 transition disabled:opacity-50 flex items-center gap-1.5"
          >
            <Zap className="w-3.5 h-3.5 text-yellow-400" />
            <span>{testing ? "Testing..." : "Test Connection"}</span>
          </button>

          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 rounded-xl text-zinc-400 hover:text-white text-xs font-medium transition"
            >
              Cancel
            </button>
            <button
              type="button"
              onClick={handleSave}
              className="px-5 py-2 rounded-xl bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white text-xs font-bold shadow-lg shadow-purple-600/30 transition"
            >
              Save & Activate Provider
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

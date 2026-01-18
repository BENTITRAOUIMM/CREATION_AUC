// src/AucSimActions.jsx
import React, { useState, useEffect } from "react";
import { Sun, Moon, LogOut, User } from "lucide-react";
import logo from "./assets/logo_ooredoo.png";
import { creation_liberation_sim } from "./creation_liberation_sim";
import { useTheme } from "./useTheme";
import { jwtDecode } from "jwt-decode";



function AucSimActions({ username: initialUsername, onLogout }) {
  const [theme, setTheme] = useTheme();

  const [username] = useState(initialUsername || "Utilisateur inconnu");
  const [simData, setSimData] = useState("");
  const [logs, setLogs] = useState([]);
  const [isProcessing, setIsProcessing] = useState(false);
  const [userType, setUserType] = useState("");


const ACCESS_RULES = {
  PROD_ONLY: ["boa_activations"],
  UAT_ONLY: ["crm_it_team", "digital_factory", "roaming_team"],
  BOTH: ["support1515"]
};

const canAccessPROD = (userType) =>
  ACCESS_RULES.PROD_ONLY.includes(userType) ||
  ACCESS_RULES.BOTH.includes(userType);

const canAccessUAT = (userType) =>
  ACCESS_RULES.UAT_ONLY.includes(userType) ||
  ACCESS_RULES.BOTH.includes(userType);


useEffect(() => {
  try {
    const token = localStorage.getItem("token");
    if (!token) {
      setUserType("");
      return;
    }

    const decoded = jwtDecode(token);
    setUserType(decoded.userType || "");

  } catch (e) {
    console.error("Token invalide", e);
    setUserType("");
  }
}, []);

  const isProdAllowed = canAccessPROD(userType);
  const isUatAllowed  = canAccessUAT(userType);
  
 
  const lineCount = simData.trim() ? simData.split("\n").length : 0;

  const resetViews = () => setLogs([]);

  const handleSubmit = async (env) => {
    if (!simData.trim()) {
      setLogs([{ status: "ERROR", message: "Please enter at least one ICCID." }]);
      return;
    }

    setIsProcessing(true);
    setLogs([]);

    try {
      const lines = simData
        .split(/\r?\n/)
        .map((l) => l.trim())
        .filter(Boolean);

      const result = await creation_liberation_sim({
        mode: "batch",
        data: lines,
        environment: env,
      });

      // ✅ Log parsing amélioré pour détecter les SUCCESS par message
      const parsedLogs = (result.statusList || []).map((item) => {
        const rawStatus = item.status?.toUpperCase() || "";
        const message = item.message || "";

        const isSuccess =
          rawStatus === "SUCCESS" ||
          /SIM libérée|AUC générée/i.test(message);

        return {
          ...item,
          status: isSuccess ? "SUCCESS" : "ERROR",
          message,
        };
      });

      setLogs(parsedLogs);
    } catch (e) {
      setLogs([{ status: "ERROR", message: e.message || "Erreur inattendue" }]);
    } finally {
      setIsProcessing(false);
    }
  };

  // Download logs
  const downloadLogs = () => {
    if (!logs.length) return;

    const content = logs
      .map((l) => `[${l.status}] ${l.sim || ""}: ${l.message}`)
      .join("\n");

    const blob = new Blob([content], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);

    const a = document.createElement("a");
    a.href = url;
    a.download = "auc_sim_logs.txt";
    a.click();

    URL.revokeObjectURL(url);
  };

  // Button styles (lighter, more modern)
  const btnBase =
    "px-5 py-2 text-sm rounded-full font-semibold transition transform-gpu flex items-center gap-2 shadow-sm hover:shadow-md disabled:opacity-50 disabled:cursor-not-allowed";
  const btnUAT =
    btnBase +
    " bg-white border border-gray-200 hover:bg-gray-50 text-gray-700 dark:bg-gray-800 dark:border-gray-700 dark:hover:bg-gray-700 dark:text-gray-100";
  const btnPROD = btnUAT; // Même color palette for PROD
  const btnDownload =
    btnBase +
    " bg-white border border-gray-200 hover:bg-gray-50 text-gray-700 dark:bg-gray-800 dark:border-gray-700 dark:hover:bg-gray-700 dark:text-gray-100";

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 dark:text-gray-100 transition-colors">
        {/* HEADER */}
      <header className="bg-white dark:bg-gray-800 px-6 py-4 flex justify-between items-center">
        <img src={logo} alt="logo" className="h-10" />

        <div className="flex items-center gap-4">
          {/* Username */}
          <div className="px-4 py-1.5 rounded-full text-sm font-bold bg-gray-100 text-gray-900 dark:bg-gray-800 dark:text-gray-100 border border-gray-300 dark:border-gray-700">
            {username.toUpperCase()}
          </div>

          <User size={24} className="text-gray-900 dark:text-gray-100" />

          {/* Theme toggle – FIXED */}
          <button
            onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
            className="
              p-2 rounded-full
              text-gray-900 dark:text-gray-100
              hover:bg-gray-200 dark:hover:bg-gray-700
              transition-colors
            "
            title="Changer le thème"
          >
            {theme === "dark" ? <Sun size={22} /> : <Moon size={22} />}
          </button>

          {/* Logout – FIXED */}
          <button
            onClick={onLogout}
            className="
              p-2 rounded-full
              text-gray-900 dark:text-gray-100
              hover:bg-gray-200 dark:hover:bg-gray-700
              transition-colors
            "
            title="Déconnexion"
          >
            <LogOut size={22} />
          </button>
        </div>
      </header>

      {/* Divider */}
      <div className="h-px bg-gray-200 dark:bg-gray-700" />

      {/* MAIN */}
      <main className="container mx-auto px-4 py-8">
        {/* INTRO */}
        <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl p-6 mb-8">
          <h1 className="text-3xl font-extrabold text-gray-900 dark:text-red-500 mb-2">
            AUC Creation & SIM Release
          </h1>
          <p className="text-gray-700 dark:text-gray-300">
            Create AUC and Release SIM's in PROD & UAT environment.
          </p>
        </div>

        {/* CONTENT */}
        <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl p-6 grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* LEFT */}
          <div>
            <div className="flex justify-between mb-2">
              <label className="text-base font-semibold text-gray-900 dark:text-gray-200">
                Paste Your SIM's Here
              </label>
              <span className="text-sm text-gray-500 dark:text-gray-400">
                Lines: {lineCount}
              </span>
            </div>

            <textarea
              value={simData}
              onChange={(e) => setSimData(e.target.value)}
              placeholder="8921303022229842679F"
              className="
                w-full h-64 p-4 rounded-lg font-mono text-sm resize-none
                border border-gray-300 dark:border-gray-600
                bg-white dark:bg-gray-900
                text-gray-900 dark:text-gray-100
                placeholder-gray-400 dark:placeholder-gray-500
                focus:ring-2 focus:ring-red-500
              "
            />
          </div>

          {/* RIGHT */}
          <div>
            <div className="flex justify-between mb-2 items-center">
              <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
                Activity Logs
              </h2>
              <button
                onClick={resetViews}
                className="text-md px-4 py-1 rounded-lg bg-red-600 text-white hover:bg-red-400 dark:bg-gray-900 dark:text-red-400 dark:hover:bg-gray-800"
              >
                Clear All
              </button>
            </div>

           
            {/* Logs */}
            <div className="h-64 overflow-y-auto bg-gray-50 dark:bg-gray-900 rounded-lg p-3 space-y-1 font-mono text-sm">
              {logs.length === 0 && (
                <p className="text-sm font-medium text-gray-500 dark:text-gray-400 italic">
                  Logs will be displayed here
                </p>
              )}
              {logs.map((l, i) => (
                <p
                  key={i}
                  className={`px-3 py-2 rounded-lg text-sm flex items-start gap-2 ${
                    l.status === "SUCCESS"
                      ? "bg-green-50 text-green-700 dark:bg-green-900 dark:text-green-200"
                      : "bg-red-50 text-red-700 dark:bg-red-900 dark:text-red-200"
                  }`}
                >
                  <span>{l.status === "SUCCESS" ? "✔" : "✖"}</span>
                  <span className="break-all font-semibold">
                    <strong>{l.sim || "SIM"}:</strong> {l.message}
                  </span>
                </p>
              ))}
            </div>

            {/* Counter */}
            <div className="flex gap-4 text-sm font-semibold mb-2 justify-end">
              <span className="text-green-600">
                ✔ {logs.filter((l) => l.status === "SUCCESS").length} Success
              </span>
              <span className="text-red-600">
                ✖ {logs.filter((l) => l.status !== "SUCCESS").length} Errors
              </span>
            </div>

            {/* Sticky Action Buttons */}
            <div className="sticky bottom-0 mt-6 bg-white/90 dark:bg-gray-900/90 backdrop-blur  dark:border-gray-700 rounded-xl py-3 px-2">
              <div className="flex flex-wrap justify-center gap-3">

                <button
                  onClick={() => handleSubmit("PROD")}
                  disabled={!isProdAllowed || isProcessing}
                  title={!isProdAllowed ? "Access denied" : undefined}
                  className={
                    !isProdAllowed
                      ? btnBase + " bg-gray-200 text-gray-500 dark:bg-gray-700 dark:text-gray-400 disabled:cursor-not-allowed"
                      : btnPROD
                  }
                >
                  Liberate in PROD

                 </button>

                <button
                  onClick={() => handleSubmit("UAT")}
                  disabled={!isUatAllowed || isProcessing}
                  title={!isUatAllowed ? "Access denied" : undefined}
                  className={
                    !isUatAllowed
                      ? btnBase + " bg-gray-200 text-gray-500 dark:bg-gray-700 dark:text-gray-400 disabled:cursor-not-allowed"
                      : btnUAT
                  }
                >
                  Liberate in UAT
                </button>

                <button
                  onClick={downloadLogs}
                  disabled={!logs.length}
                  className={btnDownload}
                >
                  Download Logs
                </button>
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}

export default AucSimActions;

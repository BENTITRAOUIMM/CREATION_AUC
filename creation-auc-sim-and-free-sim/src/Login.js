// src/Login.jsx
import React, { useState } from "react";
import logo from "./assets/logo_ooredoo.png";

function Login({ onAuthSuccess }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [authMessage, setAuthMessage] = useState("");
  const [messageType, setMessageType] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const authenticate = async (e) => {
    e.preventDefault();

    if (isSubmitting) return;

    const trimmedUsername = username.trim();
    const trimmedPassword = password.trim();

    if (!trimmedUsername || !trimmedPassword) {
      showMessage(
        "Le nom d'utilisateur et le mot de passe sont obligatoires",
        "error"
      );
      return;
    }

    const apiEndpoint = "http://10.2.145.60:5012/auth/login";

    setIsSubmitting(true);

    try {
      const response = await fetch(apiEndpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          username: trimmedUsername,
          password: trimmedPassword,
        }),
      });

      const data = await response.json();

      if (response.ok) {
        if (data.accessToken) {
          localStorage.setItem("token", data.accessToken);
          localStorage.setItem("date_expires", data.tokenExpDate);
          localStorage.setItem("username", trimmedUsername);
          showMessage("Authentification réussie !", "success");
          onAuthSuccess(trimmedUsername);
        } else {
          showMessage("Une erreur inconnue est survenue.", "error");
        }
      } else {
        switch (response.status) {
          case 400:
            showMessage(
              "Le nom d'utilisateur et le mot de passe sont obligatoires",
              "error"
            );
            break;
          case 401:
            showMessage("Utilisateur ou mot de passe incorrect", "error");
            break;
          case 403:
            showMessage("Accès refusé", "error");
            break;
          default:
            showMessage(
              "Erreur inconnue : Veuillez réessayer plus tard",
              "error"
            );
            break;
        }
      }
    } catch (error) {
      console.error("Erreur de requête:", error);
      showMessage("Une erreur s'est produite lors de la demande", "error");
    } finally {
      setIsSubmitting(false);
    }
  };

  const showMessage = (message, type) => {
    setAuthMessage(message);
    setMessageType(type);
  };

  const clearMessage = () => {
    setAuthMessage("");
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-gray-50 via-gray-100 to-gray-200 px-4">
      <div className="w-full max-w-sm">
        {/* Card */}
        <div className="bg-white rounded-3xl shadow-xl border border-gray-200 p-8">
          {/* Logo */}
          <div className="flex justify-center mb-8">
            <img src={logo} alt="Logo Ooredoo" className="h-16" />
          </div>

          {/* Title */}
          <h1 className="text-xl font-semibold text-center text-gray-800 mb-2">
            AUC Creation & SIM Release
          </h1>
          <p className="text-center text-gray-500 text-sm mb-8">
            Enter your credentials to continue
          </p>

          {/* Form */}
          <form className="space-y-5" onSubmit={authenticate}>
            {/* Username */}
            <div className="flex flex-col items-center">
              <input
                id="username"
                type="text"
                placeholder="Username"
                value={username}
                onChange={(e) => {
                  setUsername(e.target.value);
                  clearMessage();
                }}
                className="w-72 rounded-full border border-gray-300 bg-gray-50 focus:bg-white shadow-sm focus:border-red-500 focus:ring-1 focus:ring-red-400 focus:outline-none text-sm h-12 px-5 transition"
                required
              />
            </div>

            {/* Password */}
            <div className="flex flex-col items-center">
              <input
                id="password"
                type="password"
                placeholder="Password"
                value={password}
                onChange={(e) => {
                  setPassword(e.target.value);
                  clearMessage();
                }}
                className="w-72 rounded-full border border-gray-300 bg-gray-50 focus:bg-white shadow-sm focus:border-red-500 focus:ring-1 focus:ring-red-400 focus:outline-none text-sm h-12 px-5 transition"
                required
              />
            </div>

            {/* Submit */}
            <div className="flex justify-center">
              <button
                type="submit"
                disabled={isSubmitting}
                className="w-72 rounded-full py-3 px-4 text-base font-semibold text-white shadow-md bg-gradient-to-r from-red-500 via-red-600 to-red-500 hover:scale-105 hover:shadow-lg focus:outline-none focus:ring-2 focus:ring-red-400 transition-all duration-300 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isSubmitting ? "Signing in..." : "Login"}
              </button>
            </div>
          </form>
          <p class="text-center text-xs text-[var(--text-secondary)] mt-3">© Internal App – Developed by <span class="text-red-600"> Support1515 </span>
          </p>

          {/* Messages */}
          {authMessage && (
            <div
              className={`mt-5 text-center text-sm font-medium px-4 py-2 rounded-full ${
                messageType === "success"
                  ? "bg-green-100 text-green-700"
                  : "bg-red-100 text-red-600"
              }`}
            >
              {authMessage}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default Login;
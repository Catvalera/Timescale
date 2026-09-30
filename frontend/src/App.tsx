import { useEffect, useState } from "react";
import { Navigate, Route, Routes, useNavigate } from "react-router-dom";
import { session, setSessionExpiredHandler, type User } from "./api";
import Dashboard from "./pages/Dashboard";
import Login from "./pages/Login";
import Register from "./pages/Register";
import Verify from "./pages/Verify";

export default function App() {
  const navigate = useNavigate();
  const [user, setUser] = useState<User | null>(() => (session.hasTokens() ? session.user() : null));

  useEffect(() => {
    setSessionExpiredHandler(() => {
      setUser(null);
      navigate("/login", { replace: true, state: { notice: "Сессия истекла. Войдите снова." } });
    });
  }, [navigate]);

  return (
    <Routes>
      <Route path="/login" element={user ? <Navigate to="/" replace /> : <Login />} />
      <Route path="/register" element={user ? <Navigate to="/" replace /> : <Register />} />
      <Route path="/verify" element={<Verify onAuthorized={setUser} />} />
      <Route path="/" element={user ? <Dashboard user={user} onLogout={() => setUser(null)} /> : <Navigate to="/login" replace />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

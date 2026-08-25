import React from "react";
import "@/App.css";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import Landing from "@/pages/Landing";
import Auth from "@/pages/Auth";
import Onboarding from "@/pages/Onboarding";
import Chat from "@/pages/Chat";
import Admin from "@/pages/Admin";
import { Loader2 } from "lucide-react";

function FullLoader() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-background">
      <Loader2 className="h-6 w-6 animate-spin text-primary" />
    </div>
  );
}

function Protected({ children, adminOnly }) {
  const { user, loading } = useAuth();
  if (loading) return <FullLoader />;
  if (!user) return <Navigate to="/auth" replace />;
  if (!user.onboarded && !user.is_admin) return <Navigate to="/onboarding" replace />;
  if (adminOnly && !user.is_admin) return <Navigate to="/chat" replace />;
  return children;
}

export default function App() {
  const { user, loading } = useAuth();
  return (
    <div className="App grain">
      <BrowserRouter>
        <Routes>
          <Route path="/" element={loading ? <FullLoader /> : user ? <Navigate to={user.is_admin ? "/admin" : "/chat"} replace /> : <Landing />} />
          <Route path="/auth" element={user ? <Navigate to={user.is_admin ? "/admin" : "/chat"} replace /> : <Auth />} />
          <Route path="/onboarding" element={<Onboarding />} />
          <Route path="/chat" element={<Protected><Chat /></Protected>} />
          <Route path="/admin" element={<Protected adminOnly><Admin /></Protected>} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </div>
  );
}

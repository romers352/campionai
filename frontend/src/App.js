import React from "react";
import "@/App.css";
import { BrowserRouter, Routes, Route, Navigate, useLocation } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import Landing from "@/pages/Landing";
import Auth from "@/pages/Auth";
import ResetPassword from "@/pages/ResetPassword";
import AuthCallback from "@/components/AuthCallback";
import Onboarding from "@/pages/Onboarding";
import Chat from "@/pages/Chat";
import Admin from "@/pages/Admin";
import Wellness from "@/pages/Wellness";
import Billing from "@/pages/Billing";
import Doctors from "@/pages/Doctors";
import MyConsults from "@/pages/MyConsults";
import ConsultRoom from "@/pages/ConsultRoom";
import DoctorApply from "@/pages/DoctorApply";
import DoctorDashboard from "@/pages/DoctorDashboard";
import { PaymentSuccess, PaymentCancel } from "@/pages/PaymentReturn";
import About from "@/pages/About";
import Contact from "@/pages/Contact";
import FAQ from "@/pages/FAQ";
import Privacy from "@/pages/Privacy";
import Terms from "@/pages/Terms";
import Safety from "@/pages/Safety";
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
  // Doctors skip patient onboarding — they have their own application flow.
  if (!user.onboarded && !user.is_admin && user.role !== "doctor") return <Navigate to="/onboarding" replace />;
  if (adminOnly && !user.is_admin) return <Navigate to="/chat" replace />;
  return children;
}

/** Doctor-only. Applicants who aren't verified yet land on the application page,
 *  which is where their status and next step live. */
function DoctorOnly({ children }) {
  const { user, loading } = useAuth();
  if (loading) return <FullLoader />;
  if (!user) return <Navigate to="/auth" replace />;
  if (user.role !== "doctor") return <Navigate to="/doctor/apply" replace />;
  return children;
}

function homeFor(user) {
  if (user.is_admin) return "/admin";
  if (user.role === "doctor") return "/doctor";
  return "/chat";
}

export default function App() {
  return (
    <div className="App grain">
      <BrowserRouter>
        <AppInner />
      </BrowserRouter>
    </div>
  );
}

function AppInner() {
  const { user, loading } = useAuth();
  const location = useLocation();

  // Emergent Google OAuth returns to {redirect}#session_id=... — intercept it
  // synchronously (before any Protected route runs) and hand off to AuthCallback.
  if (location.hash && location.hash.includes("session_id=")) {
    return <AuthCallback />;
  }

  return (
    <Routes>
      <Route path="/" element={loading ? <FullLoader /> : user ? <Navigate to={homeFor(user)} replace /> : <Landing />} />
      <Route path="/auth" element={user ? <Navigate to={homeFor(user)} replace /> : <Auth />} />
      <Route path="/reset-password" element={<ResetPassword />} />
      <Route path="/onboarding" element={<Onboarding />} />
      {/* Public content pages */}
      <Route path="/about" element={<About />} />
      <Route path="/contact" element={<Contact />} />
      <Route path="/faq" element={<FAQ />} />
      <Route path="/privacy" element={<Privacy />} />
      <Route path="/terms" element={<Terms />} />
      <Route path="/safety" element={<Safety />} />

      <Route path="/chat" element={<Protected><Chat /></Protected>} />
      <Route path="/wellness" element={<Protected><Wellness /></Protected>} />
      <Route path="/billing" element={<Protected><Billing /></Protected>} />

      {/* Human consultations */}
      <Route path="/doctors" element={<Protected><Doctors /></Protected>} />
      <Route path="/consults" element={<Protected><MyConsults /></Protected>} />
      <Route path="/consult/:sessionId" element={<Protected><ConsultRoom /></Protected>} />

      {/* Doctor side */}
      <Route path="/doctor/apply" element={<Protected><DoctorApply /></Protected>} />
      <Route path="/doctor" element={<DoctorOnly><DoctorDashboard /></DoctorOnly>} />

      <Route path="/payment/success" element={<Protected><PaymentSuccess /></Protected>} />
      <Route path="/payment/cancel" element={<Protected><PaymentCancel /></Protected>} />
      <Route path="/admin" element={<Protected adminOnly><Admin /></Protected>} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

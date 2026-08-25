import React, { useEffect, useState } from "react";
import { PayPalScriptProvider, PayPalButtons } from "@paypal/react-paypal-js";
import { api } from "@/lib/api";
import { toast } from "@/components/ui/sonner";
import { Loader2 } from "lucide-react";

/**
 * Pays for a single consultation. The backend already created the PayPal order when
 * the session was booked, so this only approves and captures it — the order id is
 * server-issued and tied to the session, never chosen by the client.
 */
export default function PayPalConsultPay({ sessionId, orderId, onPaid }) {
  const [clientId, setClientId] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.get("/pricing")
      .then(({ data }) => setClientId(data.paypal_client_id))
      .catch(() => setClientId(null))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="flex justify-center py-6"><Loader2 className="h-5 w-5 animate-spin text-primary" /></div>;
  if (!clientId) return <p className="text-sm text-muted-foreground py-4">Payments aren't set up yet — please try a volunteer doctor.</p>;

  return (
    <div data-testid="consult-pay">
      <PayPalScriptProvider options={{ clientId, intent: "capture", components: "buttons", dataNamespace: "paypal_consult" }}>
        <PayPalButtons
          style={{ layout: "vertical", color: "gold", shape: "pill", label: "pay", height: 44, tagline: false }}
          createOrder={() => orderId}
          onApprove={async () => {
            try {
              await api.post(`/consults/${sessionId}/pay/${orderId}`);
              onPaid?.();
            } catch (e) {
              toast.error(e?.response?.data?.detail || "Payment couldn't be confirmed");
            }
          }}
          onError={() => toast.error("PayPal error — please try again")}
        />
      </PayPalScriptProvider>
    </div>
  );
}

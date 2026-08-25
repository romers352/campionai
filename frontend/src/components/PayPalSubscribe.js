import React from "react";
import { PayPalScriptProvider, PayPalButtons } from "@paypal/react-paypal-js";
import { api } from "@/lib/api";
import { toast } from "@/components/ui/sonner";

const CID = process.env.REACT_APP_PAYPAL_CLIENT_ID;
const PLANS = {
  monthly: process.env.REACT_APP_PAYPAL_PLAN_MONTHLY,
  yearly: process.env.REACT_APP_PAYPAL_PLAN_YEARLY,
};

export function paypalConfigured() {
  return !!CID && (!!PLANS.monthly || !!PLANS.yearly);
}

export default function PayPalSubscribe({ planKey, onActivated }) {
  const plan_id = PLANS[planKey];
  if (!CID || !plan_id) return null;
  return (
    <div data-testid={`paypal-${planKey}`}>
      <PayPalScriptProvider options={{ clientId: CID, intent: "subscription", vault: true, components: "buttons" }}>
        <PayPalButtons
          style={{ layout: "horizontal", color: "gold", shape: "pill", label: "subscribe", height: 44, tagline: false }}
          createSubscription={(data, actions) => actions.subscription.create({ plan_id })}
          onApprove={async (data) => {
            try {
              await api.post("/paypal/activate", { subscription_id: data.subscriptionID, plan_key: planKey });
              toast.success("PayPal subscription active — welcome to Plus!");
              onActivated?.();
            } catch (e) {
              toast.error(e?.response?.data?.detail || "Could not activate subscription");
            }
          }}
          onError={() => toast.error("PayPal error — please try again")}
        />
      </PayPalScriptProvider>
    </div>
  );
}

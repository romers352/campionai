import React from "react";
import { PayPalScriptProvider, PayPalButtons } from "@paypal/react-paypal-js";
import { api } from "@/lib/api";
import { toast } from "@/components/ui/sonner";

/**
 * PayPal is the only payment rail. Client id and plan ids come from GET /api/pricing
 * so prices and plans live in exactly one place (the backend) — changing a price
 * never requires a frontend rebuild.
 *
 * Subscriptions and one-time orders need different SDK intents, so each provider
 * loads under its own dataNamespace to avoid clobbering the other.
 */

export default function PayPalSubscribe({ clientId, planId, planKey, onActivated }) {
  if (!clientId || !planId) return null;
  return (
    <div data-testid={`paypal-${planKey}`}>
      <PayPalScriptProvider
        options={{
          clientId,
          intent: "subscription",
          vault: true,
          components: "buttons",
          dataNamespace: "paypal_subs",
        }}
      >
        <PayPalButtons
          style={{ layout: "horizontal", color: "gold", shape: "pill", label: "subscribe", height: 44, tagline: false }}
          createSubscription={(data, actions) => actions.subscription.create({ plan_id: planId })}
          onApprove={async (data) => {
            try {
              await api.post("/paypal/activate", { subscription_id: data.subscriptionID, plan_key: planKey });
              toast.success("You're on Plus — welcome.");
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

export function PayPalDonate({ clientId, amount, anonymous, onDone, disabled }) {
  if (!clientId || !amount || amount < 1) return null;
  return (
    <div data-testid="paypal-donate" className={disabled ? "pointer-events-none opacity-50" : ""}>
      <PayPalScriptProvider
        options={{ clientId, intent: "capture", components: "buttons", dataNamespace: "paypal_orders" }}
      >
        <PayPalButtons
          forceReRender={[amount, anonymous]}
          style={{ layout: "horizontal", color: "white", shape: "pill", label: "paypal", height: 44, tagline: false }}
          createOrder={async () => {
            const { data } = await api.post("/donations/order", { amount, anonymous: !!anonymous });
            return data.order_id;
          }}
          onApprove={async (data) => {
            try {
              const res = await api.post(`/donations/capture/${data.orderID}`);
              onDone?.(res.data);
            } catch (e) {
              toast.error(e?.response?.data?.detail || "Could not complete the donation");
            }
          }}
          onError={() => toast.error("PayPal error — please try again")}
        />
      </PayPalScriptProvider>
    </div>
  );
}

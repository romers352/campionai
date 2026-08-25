import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
export const API = `${BACKEND_URL}/api`;

export const api = axios.create({ baseURL: API });

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("campion_token");
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

api.interceptors.response.use(
  (r) => r,
  (err) => {
    if (err?.response?.status === 401) {
      localStorage.removeItem("campion_token");
    }
    return Promise.reject(err);
  }
);

// SSE streaming for chat
export async function streamChat({ body, onMeta, onDelta, onDone, onError }) {
  const token = localStorage.getItem("campion_token");
  try {
    const res = await fetch(`${API}/chat/stream`, {
      method: "POST",
      headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
      body: JSON.stringify(body),
    });
    if (!res.ok || !res.body) throw new Error("stream failed");
    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      let idx;
      while ((idx = buffer.indexOf("\n\n")) >= 0) {
        const raw = buffer.slice(0, idx).trim();
        buffer = buffer.slice(idx + 2);
        if (raw.startsWith("data: ")) {
          const obj = JSON.parse(raw.slice(6));
          if (obj.type === "meta") onMeta?.(obj);
          else if (obj.type === "delta") onDelta?.(obj.content);
          else if (obj.type === "done") onDone?.(obj);
        }
      }
    }
  } catch (e) {
    onError?.(e);
  }
}

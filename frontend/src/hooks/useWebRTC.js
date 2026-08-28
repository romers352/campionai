import { useCallback, useEffect, useRef, useState } from "react";
import { API } from "@/lib/api";

/**
 * Raw WebRTC over our own WebSocket signaling — no vendor SFU.
 *
 * Media is peer-to-peer and never reaches the server. The "polite peer" pattern
 * below is what stops two simultaneous offers from deadlocking: the patient is
 * polite (rolls back on collision), the doctor is impolite (ignores the incoming
 * offer and keeps its own). Without it, both sides can end up stuck in
 * have-local-offer forever.
 */
export default function useWebRTC({ sessionId, mode = "video", isDoctor = false, onChat, onEnded }) {
  const [status, setStatus] = useState("connecting"); // connecting | waiting | live | ended | failed
  const [peerPresent, setPeerPresent] = useState(false);
  const [micOn, setMicOn] = useState(mode !== "chat");
  const [camOn, setCamOn] = useState(mode === "video");
  const [peerMedia, setPeerMedia] = useState({ mic: true, cam: mode === "video" });
  const [error, setError] = useState(null);

  const localVideo = useRef(null);
  const remoteVideo = useRef(null);
  const pc = useRef(null);
  const ws = useRef(null);
  const localStream = useRef(null);
  const makingOffer = useRef(false);
  const ignoreOffer = useRef(false);
  const closedByUs = useRef(false);
  const polite = !isDoctor; // exactly one side must be polite

  const send = useCallback((obj) => {
    if (ws.current?.readyState === WebSocket.OPEN) ws.current.send(JSON.stringify(obj));
  }, []);

  const sendChat = useCallback((text) => {
    if (text?.trim()) send({ type: "chat", text: text.trim() });
  }, [send]);

  const toggleMic = useCallback(() => {
    const track = localStream.current?.getAudioTracks()[0];
    if (!track) return;
    track.enabled = !track.enabled;
    setMicOn(track.enabled);
    send({ type: "media-state", mic: track.enabled, cam: camOn });
  }, [send, camOn]);

  const toggleCam = useCallback(() => {
    const track = localStream.current?.getVideoTracks()[0];
    if (!track) return;
    track.enabled = !track.enabled;
    setCamOn(track.enabled);
    send({ type: "media-state", mic: micOn, cam: track.enabled });
  }, [send, micOn]);

  const hangup = useCallback(() => {
    closedByUs.current = true;
    send({ type: "hangup" });
    localStream.current?.getTracks().forEach((t) => t.stop());
    pc.current?.close();
    ws.current?.close();
    setStatus("ended");
    onEnded?.();
  }, [send, onEnded]);

  useEffect(() => {
    if (!sessionId) return undefined;
    let cancelled = false;
    let heartbeat;

    const start = async () => {
      // 1. Local media first — a permission denial should surface before we dial out.
      if (mode !== "chat") {
        try {
          const stream = await navigator.mediaDevices.getUserMedia({
            audio: true,
            video: mode === "video" ? { width: { ideal: 1280 }, height: { ideal: 720 } } : false,
          });
          if (cancelled) { stream.getTracks().forEach((t) => t.stop()); return; }
          localStream.current = stream;
          if (localVideo.current) localVideo.current.srcObject = stream;
        } catch (e) {
          setError(
            e?.name === "NotAllowedError"
              ? "Camera and microphone access was blocked. Allow it in your browser, then rejoin."
              : "Couldn't reach your camera or microphone."
          );
          setStatus("failed");
          return;
        }
      }

      // 2. Signaling socket. Token goes in the first message, never the URL.
      const token = localStorage.getItem("campion_token");
      const url = `${API.replace(/^http/, "ws")}/rtc/${sessionId}`;
      const socket = new WebSocket(url);
      ws.current = socket;

      socket.onopen = () => socket.send(JSON.stringify({ token }));

      socket.onclose = (ev) => {
        if (cancelled || closedByUs.current) return;
        if (ev.code >= 4400 && ev.code <= 4409) {
          setError(ev.reason || "Couldn't join this session.");
          setStatus("failed");
        } else if (status !== "ended") {
          setStatus("ended");
          onEnded?.();
        }
      };
      socket.onerror = () => { if (!cancelled && !closedByUs.current) setError("Connection problem."); };

      socket.onmessage = async (ev) => {
        let msg;
        try { msg = JSON.parse(ev.data); } catch { return; }

        if (msg.type === "joined") {
          buildPeer(msg.iceServers);
          setPeerPresent(!!msg.peer_present);
          setStatus(msg.peer_present ? "live" : "waiting");
          // The doctor drives the first offer, so both sides never open simultaneously.
          if (msg.peer_present && isDoctor) negotiate();
          heartbeat = setInterval(() => send({ type: "ping" }), 25000);
        } else if (msg.type === "peer-joined") {
          setPeerPresent(true);
          setStatus("live");
          if (isDoctor) negotiate();
        } else if (msg.type === "peer-left") {
          setPeerPresent(false);
          setStatus("waiting");
        } else if (msg.type === "chat") {
          onChat?.(msg);
        } else if (msg.type === "media-state") {
          setPeerMedia({ mic: !!msg.mic, cam: !!msg.cam });
        } else if (msg.type === "hangup") {
          closedByUs.current = true;
          setStatus("ended");
          onEnded?.();
        } else if (msg.type === "offer" || msg.type === "answer") {
          await onDescription(msg);
        } else if (msg.type === "ice-candidate" && msg.candidate) {
          try { await pc.current?.addIceCandidate(msg.candidate); }
          catch (e) { if (!ignoreOffer.current) console.warn("ICE add failed", e); }
        }
      };
    };

    const buildPeer = (iceServers) => {
      if (pc.current || mode === "chat") return;
      const conn = new RTCPeerConnection({ iceServers: iceServers || [] });
      pc.current = conn;

      localStream.current?.getTracks().forEach((t) => conn.addTrack(t, localStream.current));

      conn.ontrack = (ev) => {
        if (remoteVideo.current && ev.streams[0]) remoteVideo.current.srcObject = ev.streams[0];
      };
      conn.onicecandidate = (ev) => {
        if (ev.candidate) send({ type: "ice-candidate", candidate: ev.candidate.toJSON() });
      };
      conn.onnegotiationneeded = () => { if (isDoctor) negotiate(); };
      conn.onconnectionstatechange = () => {
        if (conn.connectionState === "failed") {
          // Full ICE restart — cheaper than tearing the whole session down.
          conn.restartIce?.();
          setError("Connection dropped — trying to reconnect.");
        } else if (conn.connectionState === "connected") {
          setError(null);
        }
      };
    };

    const negotiate = async () => {
      const conn = pc.current;
      if (!conn) return;
      try {
        makingOffer.current = true;
        await conn.setLocalDescription();
        send({ type: "offer", sdp: conn.localDescription });
      } catch (e) {
        console.warn("negotiation failed", e);
      } finally {
        makingOffer.current = false;
      }
    };

    const onDescription = async (msg) => {
      const conn = pc.current;
      if (!conn) return;
      const description = msg.sdp;
      const offerCollision =
        description.type === "offer" &&
        (makingOffer.current || conn.signalingState !== "stable");

      ignoreOffer.current = !polite && offerCollision;
      if (ignoreOffer.current) return; // impolite side keeps its own offer

      try {
        await conn.setRemoteDescription(description);
        if (description.type === "offer") {
          await conn.setLocalDescription();
          send({ type: "answer", sdp: conn.localDescription });
        }
      } catch (e) {
        console.warn("setRemoteDescription failed", e);
      }
    };

    start();

    return () => {
      cancelled = true;
      clearInterval(heartbeat);
      localStream.current?.getTracks().forEach((t) => t.stop());
      pc.current?.close();
      pc.current = null;
      ws.current?.close();
      ws.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sessionId, mode, isDoctor]);

  return {
    status, peerPresent, error, micOn, camOn, peerMedia,
    localVideo, remoteVideo, toggleMic, toggleCam, hangup, sendChat,
  };
}

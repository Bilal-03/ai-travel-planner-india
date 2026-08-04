"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { QRCodeSVG } from "qrcode.react";
import { api, type CollaborationRole, type TripKind } from "@/lib/api";
import { track } from "@/lib/analytics";

interface ShareTripProps {
  tripId: string;
  kind?: TripKind;
}

export default function ShareTrip({ tripId, kind = "single" }: ShareTripProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [copied, setCopied] = useState(false);
  const [shareUrl, setShareUrl] = useState<string | null>(null);
  const [linkRole, setLinkRole] = useState<Exclude<CollaborationRole, "owner">>("viewer");
  const [inviteEmail, setInviteEmail] = useState("");
  const [linkMessage, setLinkMessage] = useState<string | null>(null);

  const publicShareUrl =
    typeof window !== "undefined"
      ? `${window.location.origin}/trip/${tripId}`
      : `/trip/${tripId}`;
  const activeShareUrl = shareUrl || publicShareUrl;

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(activeShareUrl);
      setCopied(true);
      track("trip_shared", { tripId, kind, metadata: { source: "copy" } });
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Fallback
      const input = document.createElement("input");
      input.value = activeShareUrl;
      document.body.appendChild(input);
      input.select();
      document.execCommand("copy");
      document.body.removeChild(input);
      setCopied(true);
      track("trip_shared", { tripId, kind, metadata: { source: "copy" } });
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const shareWhatsApp = () => {
    track("trip_shared", { tripId, kind, metadata: { source: "whatsapp" } });
    window.open(
      `https://wa.me/?text=${encodeURIComponent(`Check out my India trip itinerary! 🇮🇳✈️\n${activeShareUrl}`)}`,
      "_blank"
    );
  };

  const shareTwitter = () => {
    track("trip_shared", { tripId, kind, metadata: { source: "twitter" } });
    window.open(
      `https://twitter.com/intent/tweet?text=${encodeURIComponent(`Just planned my India trip with AI! 🇮🇳✨`)}&url=${encodeURIComponent(activeShareUrl)}`,
      "_blank"
    );
  };

  const createLink = async () => {
    setLinkMessage(null);
    try {
      const link = await api.createShareLink(tripId, linkRole, inviteEmail.trim() || undefined);
      setShareUrl(link.share_url);
      setLinkMessage(`${linkRole === "editor" ? "Edit" : "View-only"} link created.`);
      track("trip_shared", { tripId, kind, metadata: { source: "collaboration_link", kind: linkRole } });
    } catch {
      setLinkMessage("Only the trip owner can create a collaboration link.");
    }
  };

  return (
    <div className="relative">
      <motion.button
        onClick={() => setIsOpen(!isOpen)}
        whileHover={{ scale: 1.05 }}
        whileTap={{ scale: 0.95 }}
        className="px-4 py-2 bg-primary hover:bg-primary-light text-white rounded-xl
                   font-medium text-sm transition-colors flex items-center gap-2"
        id="share-trip-btn"
      >
        🔗 Share Trip
      </motion.button>

      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0, y: 10, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 10, scale: 0.95 }}
            className="absolute right-0 top-12 z-50 glass p-5 rounded-xl w-72 shadow-lg"
          >
            <h4 className="font-bold text-foreground text-sm mb-3">
              Share your itinerary
            </h4>

            {/* Copy Link */}
            <div className="flex gap-2 mb-4">
              <input
                type="text"
                value={activeShareUrl}
                readOnly
                className="flex-1 px-3 py-2 bg-glass-bg border border-glass-border rounded-lg
                           text-foreground text-xs truncate"
              />
              <button
                onClick={handleCopy}
                className={`px-3 py-2 rounded-lg text-xs font-medium transition-colors ${
                  copied
                    ? "bg-success text-white"
                    : "bg-primary text-white hover:bg-primary-light"
                }`}
              >
                {copied ? "✓" : "Copy"}
              </button>
            </div>

            <div className="mb-4 rounded-lg border border-glass-border bg-background/25 p-3">
              <p className="text-[11px] font-semibold text-foreground">Invite collaborators</p>
              <div className="mt-2 grid grid-cols-[1fr_auto] gap-2">
                <input value={inviteEmail} onChange={(event) => setInviteEmail(event.target.value)} placeholder="Email (optional)" type="email" className="min-w-0 rounded-lg border border-glass-border bg-glass-bg px-2 py-2 text-xs text-foreground" />
                <select value={linkRole} onChange={(event) => setLinkRole(event.target.value as Exclude<CollaborationRole, "owner">)} className="rounded-lg border border-glass-border bg-glass-bg px-2 py-2 text-xs text-foreground">
                  <option value="viewer">Viewer</option>
                  <option value="editor">Editor</option>
                </select>
              </div>
              <button type="button" onClick={() => void createLink()} className="mt-2 w-full rounded-lg border border-primary/40 px-3 py-2 text-xs font-semibold text-primary transition hover:bg-primary/10">Create secure link</button>
              {linkMessage && <p className="mt-2 text-[11px] text-foreground-muted">{linkMessage}</p>}
            </div>

            {/* Social Share */}
            <div className="flex gap-2 mb-4">
              <button
                onClick={shareWhatsApp}
                className="flex-1 py-2 rounded-lg bg-[#25D366]/15 text-[#25D366]
                           hover:bg-[#25D366]/25 transition-colors text-sm font-medium"
              >
                WhatsApp
              </button>
              <button
                onClick={shareTwitter}
                className="flex-1 py-2 rounded-lg bg-info/15 text-info
                           hover:bg-info/25 transition-colors text-sm font-medium"
              >
                Twitter
              </button>
            </div>

            {/* QR Code */}
            <div className="flex justify-center p-3 bg-white rounded-lg">
              <QRCodeSVG value={activeShareUrl} size={120} />
            </div>

            <p className="text-center text-foreground-muted text-xs mt-2">
              Scan to view on mobile
            </p>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

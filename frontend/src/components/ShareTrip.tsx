"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { QRCodeSVG } from "qrcode.react";

interface ShareTripProps {
  tripId: string;
}

export default function ShareTrip({ tripId }: ShareTripProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [copied, setCopied] = useState(false);

  const shareUrl =
    typeof window !== "undefined"
      ? `${window.location.origin}/trip/${tripId}`
      : `/trip/${tripId}`;

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(shareUrl);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Fallback
      const input = document.createElement("input");
      input.value = shareUrl;
      document.body.appendChild(input);
      input.select();
      document.execCommand("copy");
      document.body.removeChild(input);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const shareWhatsApp = () => {
    window.open(
      `https://wa.me/?text=${encodeURIComponent(`Check out my India trip itinerary! 🇮🇳✈️\n${shareUrl}`)}`,
      "_blank"
    );
  };

  const shareTwitter = () => {
    window.open(
      `https://twitter.com/intent/tweet?text=${encodeURIComponent(`Just planned my India trip with AI! 🇮🇳✨`)}&url=${encodeURIComponent(shareUrl)}`,
      "_blank"
    );
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
                value={shareUrl}
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
              <QRCodeSVG value={shareUrl} size={120} />
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

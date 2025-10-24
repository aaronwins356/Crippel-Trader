import React, { useState } from "react";
import { updateMode } from "../lib/api";

export function ModeToggle({ mode, onChange }) {
  const [pending, setPending] = useState(false);

  const handleToggle = async () => {
    const nextMode = mode === "paper" ? "live" : "paper";
    if (nextMode === "live" && !window.confirm("Switch to live mode? Ensure API keys are configured.")) {
      return;
    }
    setPending(true);
    try {
      await updateMode(nextMode, nextMode === "live");
      onChange?.();
    } finally {
      setPending(false);
    }
  };

  return (
    <button onClick={handleToggle} disabled={pending} className="btn btn-toggle">
      Mode: {mode.toUpperCase()}
    </button>
  );
}

export default ModeToggle;

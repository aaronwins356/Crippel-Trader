import React, { useState } from "react";
import { updateAggression } from "../lib/api";

export function AggressionSlider({ aggression, onChange }) {
  const [value, setValue] = useState(aggression);
  const [pending, setPending] = useState(false);

  const handleCommit = async (newValue) => {
    setPending(true);
    try {
      await updateAggression(newValue);
      onChange?.();
    } finally {
      setPending(false);
    }
  };

  return (
    <div className="panel">
      <div className="panel-header">
        <span>Aggression</span>
        <span className="accent">{value}</span>
      </div>
      <input
        type="range"
        min={1}
        max={10}
        value={value}
        onChange={(event) => setValue(Number(event.target.value))}
        onMouseUp={() => handleCommit(value)}
        onTouchEnd={() => handleCommit(value)}
        disabled={pending}
        className="slider"
      />
    </div>
  );
}

export default AggressionSlider;

"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { apiFetch } from "@/lib/api-client";
import type { WhiteNoisePreset } from "@/types/api";

type EngineNodes = {
  ctx: AudioContext;
  source: AudioBufferSourceNode;
  filter: BiquadFilterNode;
  gain: GainNode;
};

function buildNoiseBuffer(ctx: AudioContext): AudioBuffer {
  const seconds = 2;
  const size = seconds * ctx.sampleRate;
  const buffer = ctx.createBuffer(1, size, ctx.sampleRate);
  const data = buffer.getChannelData(0);

  for (let i = 0; i < size; i += 1) {
    data[i] = Math.random() * 2 - 1;
  }

  return buffer;
}

function resolvePresetFilter(presetId: string): {
  type: BiquadFilterType;
  frequency: number;
  q: number;
} {
  if (presetId === "brown-focus") {
    return { type: "lowpass", frequency: 180, q: 0.85 };
  }
  if (presetId === "rain-soft") {
    return { type: "bandpass", frequency: 1200, q: 0.6 };
  }
  return { type: "bandpass", frequency: 650, q: 0.8 };
}

interface WhiteNoiseControlProps {
  className?: string;
}

export function WhiteNoiseControl({ className }: WhiteNoiseControlProps) {
  const [presets, setPresets] = useState<WhiteNoisePreset[]>([]);
  const [selectedPresetId, setSelectedPresetId] =
    useState<string>("brown-focus");
  const [volume, setVolume] = useState(35);
  const [isPlaying, setIsPlaying] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const engineRef = useRef<EngineNodes | null>(null);

  useEffect(() => {
    apiFetch<WhiteNoisePreset[]>("/api/v1/engagement/white-noise/presets")
      .then((items) => {
        setPresets(items);
        if (items.length > 0) {
          setSelectedPresetId(items[0].id);
        }
      })
      .catch((e) => setError(e.message));
  }, []);

  const selected = useMemo(
    () => presets.find((p) => p.id === selectedPresetId) ?? null,
    [presets, selectedPresetId],
  );

  const stopNoise = () => {
    const engine = engineRef.current;
    if (!engine) return;
    try {
      engine.source.stop();
    } catch {
      // no-op
    }
    engine.gain.disconnect();
    engine.filter.disconnect();
    engine.source.disconnect();
    void engine.ctx.close();
    engineRef.current = null;
    setIsPlaying(false);
  };

  const startNoise = async () => {
    stopNoise();

    const ctx = new window.AudioContext();
    const source = ctx.createBufferSource();
    source.buffer = buildNoiseBuffer(ctx);
    source.loop = true;

    const filter = ctx.createBiquadFilter();
    const cfg = resolvePresetFilter(selectedPresetId);
    filter.type = cfg.type;
    filter.frequency.value = cfg.frequency;
    filter.Q.value = cfg.q;

    const gain = ctx.createGain();
    gain.gain.value = Math.max(0, Math.min(1, volume / 100));

    source.connect(filter);
    filter.connect(gain);
    gain.connect(ctx.destination);

    source.start();
    engineRef.current = { ctx, source, filter, gain };
    setIsPlaying(true);
  };

  useEffect(() => {
    const engine = engineRef.current;
    if (!engine) return;
    engine.gain.gain.value = Math.max(0, Math.min(1, volume / 100));
  }, [volume]);

  useEffect(() => {
    if (!isPlaying) return;
    void startNoise();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedPresetId]);

  useEffect(() => {
    return () => stopNoise();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div
      className={`surface-card p-4 space-y-3 ${className ?? ""}`}
    >
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-slate-800">White Noise</h3>
        <span className="text-xs text-slate-500">Local presets only</span>
      </div>

      {error && (
        <p className="text-xs text-amber-700">
          Preset list unavailable. Using built-in fallback.
        </p>
      )}

      <div className="space-y-2">
        <label className="text-xs text-slate-600">Preset</label>
        <select
          value={selectedPresetId}
          onChange={(e) => setSelectedPresetId(e.target.value)}
          className="field-select"
        >
          {(presets.length > 0
            ? presets
            : [
                {
                  id: "brown-focus",
                  label: "Brown Focus",
                  description: "Warm low-frequency noise",
                },
                {
                  id: "rain-soft",
                  label: "Soft Rain",
                  description: "Light rain texture",
                },
                {
                  id: "cafe-air",
                  label: "Cafe Air",
                  description: "Mid ambience",
                },
              ]
          ).map((preset) => (
            <option key={preset.id} value={preset.id}>
              {preset.label}
            </option>
          ))}
        </select>
        {selected && (
          <p className="text-[11px] text-slate-500">{selected.description}</p>
        )}
      </div>

      <div className="space-y-2">
        <div className="flex items-center justify-between text-xs text-slate-600">
          <span>Volume</span>
          <span>{volume}%</span>
        </div>
        <input
          type="range"
          min={0}
          max={100}
          value={volume}
          onChange={(e) => setVolume(Number(e.target.value))}
          className="w-full"
        />
      </div>

      <div className="flex gap-2">
        {isPlaying ? (
          <button
            onClick={stopNoise}
            className="btn-soft flex-1"
          >
            Pause
          </button>
        ) : (
          <button
            onClick={() => void startNoise()}
            className="btn-primary flex-1"
          >
            Play
          </button>
        )}
      </div>
    </div>
  );
}

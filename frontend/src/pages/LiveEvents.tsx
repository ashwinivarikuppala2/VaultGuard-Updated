import React, { useEffect, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  Radio,
  RefreshCw,
  Terminal,
} from 'lucide-react';
import { threatService } from '../services/threatService';
import { LiveTelemetryEvent } from '../types';

export const LiveEvents: React.FC = () => {
  const [liveStream, setLiveStream] = useState<LiveTelemetryEvent[]>([]);
  const [wsConnected, setWsConnected] = useState<boolean>(false);

  // Initial fetch of recent telemetry
  const { data: initialEvents, isLoading } = useQuery({
    queryKey: ['live-threat-events'],
    queryFn: () => threatService.getLiveEvents(40),
    refetchInterval: 3000,
  });

  useEffect(() => {
    if (initialEvents) {
      setLiveStream(initialEvents);
    }
  }, [initialEvents]);

  // Establish WebSocket connection for live telemetry streaming
  useEffect(() => {
    let ws: WebSocket | null = null;
    let pingInterval: any = null;

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.host;
    const wsUrl = `${protocol}//${host}/api/v1/threats/ws`;

    try {
      ws = new WebSocket(wsUrl);

      ws.onopen = () => {
        setWsConnected(true);
        pingInterval = setInterval(() => {
          if (ws?.readyState === WebSocket.OPEN) {
            ws.send('ping');
          }
        }, 15000);
      };

      ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data);
          if (msg.type === 'LIVE_TELEMETRY' && msg.event) {
            setLiveStream((prev) => [msg.event, ...prev.slice(0, 50)]);
          }
        } catch {
          // ignore non-JSON ping/pong
        }
      };

      ws.onclose = () => {
        setWsConnected(false);
        if (pingInterval) clearInterval(pingInterval);
      };

      ws.onerror = () => {
        setWsConnected(false);
      };
    } catch {
      setWsConnected(false);
    }

    return () => {
      if (pingInterval) clearInterval(pingInterval);
      if (ws) ws.close();
    };
  }, []);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-slate-800">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-slate-100 font-mono flex items-center gap-2">
            <Radio className="w-5 h-5 text-cyan-400 animate-pulse" />
            LIVE TELEMETRY STREAM & EVENT BUS
          </h1>
          <p className="text-xs text-slate-400 mt-1 font-mono">
            Sub-second Filesystem Telemetry • Entropy Scoring • Dynamic Threat Evaluation
          </p>
        </div>
        <div className="flex items-center gap-3">
          <span
            className={`flex items-center gap-1.5 px-2.5 py-1 rounded text-[11px] font-mono ${
              wsConnected
                ? 'bg-emerald-950/60 text-emerald-400 border border-emerald-800'
                : 'bg-amber-950/60 text-amber-400 border border-amber-800'
            }`}
          >
            <span
              className={`w-2 h-2 rounded-full ${
                wsConnected ? 'bg-emerald-500 animate-ping' : 'bg-amber-500'
              }`}
            ></span>
            {wsConnected ? 'WEBSOCKET ACTIVE (REAL-TIME)' : 'POLLING FALLBACK (3s)'}
          </span>
        </div>
      </div>

      {/* Terminal-Style Streaming Console */}
      <div className="rounded-lg bg-slate-950 border border-slate-800 p-4 font-mono text-xs shadow-2xl space-y-3">
        <div className="flex items-center justify-between pb-2 border-b border-slate-900 text-slate-500">
          <div className="flex items-center gap-2">
            <Terminal className="w-4 h-4 text-cyan-400" />
            <span>telemetry_stream.log</span>
          </div>
          <span className="text-[11px]">{liveStream.length} buffer events</span>
        </div>

        <div className="space-y-2 max-h-[600px] overflow-y-auto pr-2 divide-y divide-slate-900/80">
          {liveStream.length > 0 ? (
            liveStream.map((item) => (
              <div key={item.id} className="pt-2 flex flex-col md:flex-row md:items-center justify-between gap-2 hover:bg-slate-900/30 px-2 py-1.5 rounded transition-colors">
                <div className="flex items-start md:items-center gap-3">
                  <span
                    className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${
                      item.risk_score >= 70
                        ? 'bg-red-950 text-red-400 border border-red-800'
                        : item.risk_score >= 40
                        ? 'bg-amber-950 text-amber-400 border border-amber-800'
                        : 'bg-slate-800 text-slate-300'
                    }`}
                  >
                    {item.event_type}
                  </span>
                  <div>
                    <span className="text-slate-200 font-semibold">{item.file_path}</span>
                    <div className="text-[10px] text-slate-500 flex gap-3 mt-0.5">
                      <span>Entropy: <strong className="text-amber-400">{item.entropy_score.toFixed(2)}</strong>/8.0</span>
                      <span>Write Rate: <strong className="text-cyan-400">{item.write_rate.toFixed(1)}</strong>/min</span>
                      <span>Rename Rate: <strong className="text-cyan-400">{item.rename_rate.toFixed(1)}</strong>/min</span>
                      {item.canary_hit && <span className="text-red-400 font-bold">⚠️ CANARY HIT</span>}
                    </div>
                  </div>
                </div>

                <div className="flex items-center gap-4 text-right">
                  <div className="text-right">
                    <div className="text-slate-200 font-bold">Score: {item.risk_score.toFixed(1)}</div>
                    <div className="text-[10px] text-slate-500">
                      {new Date(item.created_at).toLocaleTimeString()}
                    </div>
                  </div>
                </div>
              </div>
            ))
          ) : (
            <div className="py-12 text-center text-slate-600">
              {isLoading ? (
                <div className="flex items-center justify-center gap-2">
                  <RefreshCw className="w-4 h-4 animate-spin text-cyan-400" />
                  <span>Connecting to telemetry stream...</span>
                </div>
              ) : (
                <span>No telemetry events received yet. Agent file writes will stream here in real time.</span>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};


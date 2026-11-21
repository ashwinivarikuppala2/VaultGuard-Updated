import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  ShieldAlert,
  Filter,
  RefreshCw,
  Eye,
  X,
  Radio,
} from 'lucide-react';
import { threatService } from '../services/threatService';
import { StatusBadge } from '../components/common/StatusBadge';
import { Detection } from '../types';

export const DetectionHistory: React.FC = () => {
  const [severityFilter, setSeverityFilter] = useState<string>('');
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [selectedDetection, setSelectedDetection] = useState<Detection | null>(null);

  const { data, isLoading, refetch } = useQuery({
    queryKey: ['detections-history', severityFilter, statusFilter],
    queryFn: () =>
      threatService.getDetections({
        severity: severityFilter || undefined,
        status: statusFilter || undefined,
      }),
  });

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-slate-800">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-slate-100 font-mono flex items-center gap-2">
            <ShieldAlert className="w-5 h-5 text-red-500" />
            DETECTION HISTORY & INCIDENT LOGS
          </h1>
          <p className="text-xs text-slate-400 mt-1 font-mono">
            Ransomware Heuristics • Forensic Artifacts • Anomaly Signal Drill-down
          </p>
        </div>
        <button
          onClick={() => refetch()}
          className="flex items-center gap-2 px-3 py-1.5 text-xs font-mono rounded bg-slate-900 border border-slate-800 text-slate-300 hover:text-slate-100 hover:bg-slate-800 transition-colors"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin' : ''}`} />
          Refresh Detections
        </button>
      </div>

      {/* Filters Bar */}
      <div className="flex flex-wrap items-center gap-3 p-3 rounded-lg bg-slate-900/60 border border-slate-800 text-xs font-mono">
        <Filter className="w-4 h-4 text-slate-500" />
        <span className="text-slate-400">Filters:</span>

        <select
          value={severityFilter}
          onChange={(e) => setSeverityFilter(e.target.value)}
          className="bg-slate-950 border border-slate-800 rounded px-2.5 py-1 text-slate-200 focus:outline-none focus:border-cyan-500"
        >
          <option value="">All Severities</option>
          <option value="CRITICAL">Critical</option>
          <option value="HIGH">High</option>
          <option value="MEDIUM">Medium</option>
          <option value="LOW">Low</option>
        </select>

        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="bg-slate-950 border border-slate-800 rounded px-2.5 py-1 text-slate-200 focus:outline-none focus:border-cyan-500"
        >
          <option value="">All Statuses</option>
          <option value="ACTIVE">Active</option>
          <option value="RESOLVED">Resolved</option>
          <option value="FALSE_POSITIVE">False Positive</option>
        </select>

        {(severityFilter || statusFilter) && (
          <button
            onClick={() => {
              setSeverityFilter('');
              setStatusFilter('');
            }}
            className="text-[11px] text-cyan-400 hover:underline ml-auto"
          >
            Clear Filters
          </button>
        )}
      </div>

      {/* Detections Table */}
      <div className="rounded-lg bg-slate-900/60 border border-slate-800 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs font-mono">
            <thead className="bg-slate-950/80 text-slate-400 border-b border-slate-800">
              <tr>
                <th className="py-3 px-4">Threat Name</th>
                <th className="py-3 px-4">Type</th>
                <th className="py-3 px-4">Severity</th>
                <th className="py-3 px-4">Risk Score</th>
                <th className="py-3 px-4">Confidence</th>
                <th className="py-3 px-4">Status</th>
                <th className="py-3 px-4">Timestamp</th>
                <th className="py-3 px-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60">
              {data && data.items.length > 0 ? (
                data.items.map((detection) => (
                  <tr key={detection.id} className="hover:bg-slate-800/30 transition-colors">
                    <td className="py-3 px-4 font-semibold text-slate-200 flex items-center gap-2">
                      <Radio className="w-3.5 h-3.5 text-red-400" />
                      {detection.threat_name}
                    </td>
                    <td className="py-3 px-4 text-slate-400">{detection.detection_type}</td>
                    <td className="py-3 px-4">
                      <StatusBadge status={detection.severity} />
                    </td>
                    <td className="py-3 px-4">
                      <span className="font-bold text-red-400">{detection.risk_score}</span> / 100
                    </td>
                    <td className="py-3 px-4 text-slate-300">
                      {Math.round(detection.confidence_score * 100)}%
                    </td>
                    <td className="py-3 px-4">
                      <span
                        className={`px-2 py-0.5 rounded text-[10px] ${
                          detection.status === 'ACTIVE'
                            ? 'bg-red-950 text-red-400 border border-red-800'
                            : 'bg-slate-800 text-slate-300'
                        }`}
                      >
                        {detection.status}
                      </span>
                    </td>
                    <td className="py-3 px-4 text-slate-500">
                      {new Date(detection.created_at).toLocaleString()}
                    </td>
                    <td className="py-3 px-4 text-right">
                      <button
                        onClick={() => setSelectedDetection(detection)}
                        className="p-1 rounded text-cyan-400 hover:text-cyan-300 hover:bg-slate-800 transition-colors"
                        title="View Forensic Details"
                      >
                        <Eye className="w-4 h-4" />
                      </button>
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={8} className="py-12 text-center text-slate-500">
                    No detections match the specified criteria.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Forensic Signal Drill-Down Modal */}
      {selectedDetection && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm">
          <div className="bg-slate-900 border border-slate-800 rounded-lg max-w-2xl w-full p-6 space-y-4 font-mono text-xs">
            <div className="flex items-center justify-between pb-3 border-b border-slate-800">
              <div className="flex items-center gap-2">
                <ShieldAlert className="w-5 h-5 text-red-500" />
                <h3 className="text-base font-bold text-slate-100">
                  {selectedDetection.threat_name}
                </h3>
              </div>
              <button
                onClick={() => setSelectedDetection(null)}
                className="text-slate-400 hover:text-slate-100"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="grid grid-cols-2 gap-4 py-2">
              <div>
                <span className="text-slate-400">Incident ID:</span>
                <div className="text-slate-200 break-all">{selectedDetection.id}</div>
              </div>
              <div>
                <span className="text-slate-400">Target Device ID:</span>
                <div className="text-slate-200 break-all">{selectedDetection.device_id}</div>
              </div>
              <div>
                <span className="text-slate-400">Severity:</span>
                <div><StatusBadge status={selectedDetection.severity} /></div>
              </div>
              <div>
                <span className="text-slate-400">Risk Score:</span>
                <div className="text-red-400 font-bold">{selectedDetection.risk_score} / 100</div>
              </div>
            </div>

            {/* Signals and Forensic Details */}
            <div className="p-4 rounded bg-slate-950 border border-slate-800 space-y-3">
              <h4 className="font-semibold text-cyan-400">Multi-Signal Extraction Artifacts</h4>
              {selectedDetection.details ? (
                <div className="space-y-2 text-slate-300">
                  {selectedDetection.details.file_path && (
                    <div>
                      <span className="text-slate-400">Suspect File: </span>
                      <span className="text-slate-200">{selectedDetection.details.file_path}</span>
                    </div>
                  )}
                  {selectedDetection.details.entropy !== undefined && (
                    <div>
                      <span className="text-slate-400">Shannon Entropy: </span>
                      <span className="text-amber-400 font-bold">{selectedDetection.details.entropy} / 8.0</span>
                    </div>
                  )}
                  {selectedDetection.details.rates && (
                    <div className="flex gap-4">
                      <div>Write Rate: <span className="text-cyan-400">{selectedDetection.details.rates.write_rate}/min</span></div>
                      <div>Rename Rate: <span className="text-cyan-400">{selectedDetection.details.rates.rename_rate}/min</span></div>
                    </div>
                  )}
                  {selectedDetection.details.reasons && (
                    <div>
                      <span className="text-slate-400">Trigger Reasons:</span>
                      <ul className="list-disc list-inside text-red-300 mt-1 space-y-1">
                        {selectedDetection.details.reasons.map((r: string, idx: number) => (
                          <li key={idx}>{r}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              ) : (
                <p className="text-slate-500">No additional details recorded.</p>
              )}
            </div>

            <div className="flex justify-end pt-3 border-t border-slate-800">
              <button
                onClick={() => setSelectedDetection(null)}
                className="px-4 py-1.5 rounded bg-slate-800 hover:bg-slate-700 text-slate-200"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};


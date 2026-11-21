import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Sliders,
  Plus,
  RefreshCw,
} from 'lucide-react';
import { threatService } from '../services/threatService';
import { StatusBadge } from '../components/common/StatusBadge';

export const RiskPolicies: React.FC = () => {
  const queryClient = useQueryClient();
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [ruleType, setRuleType] = useState('ENTROPY');
  const [threshold, setThreshold] = useState('7.5');
  const [weight, setWeight] = useState('30');
  const [severity, setSeverity] = useState('HIGH');
  const [action, setAction] = useState('ALERT');

  const { data: rules, isLoading, refetch } = useQuery({
    queryKey: ['threat-rules'],
    queryFn: threatService.getThreatRules,
  });

  const createRuleMutation = useMutation({
    mutationFn: () =>
      threatService.createThreatRule({
        name,
        description,
        rule_type: ruleType,
        condition: 'GREATER_THAN',
        threshold: parseFloat(threshold),
        weight: parseFloat(weight),
        severity,
        action,
        is_enabled: true,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['threat-rules'] });
      setIsModalOpen(false);
      setName('');
      setDescription('');
    },
  });

  const handleCreateRule = (e: React.FormEvent) => {
    e.preventDefault();
    if (!name || !description) return;
    createRuleMutation.mutate();
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-slate-800">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-slate-100 font-mono flex items-center gap-2">
            <Sliders className="w-5 h-5 text-cyan-400" />
            RANSOMWARE HEURISTIC & RISK POLICIES
          </h1>
          <p className="text-xs text-slate-400 mt-1 font-mono">
            Adjustable Multi-Signal Weights • Threshold Barriers • Automated Containment Rules
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={() => setIsModalOpen(true)}
            className="flex items-center gap-2 px-3 py-1.5 text-xs font-mono font-semibold rounded bg-cyan-600 hover:bg-cyan-500 text-white transition-colors"
          >
            <Plus className="w-4 h-4" />
            Add Threat Rule
          </button>
          <button
            onClick={() => refetch()}
            className="p-1.5 text-slate-400 hover:text-slate-100 hover:bg-slate-800 rounded transition-colors"
          >
            <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {/* Rules List */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 font-mono text-xs">
        {rules && rules.length > 0 ? (
          rules.map((rule) => (
            <div
              key={rule.id}
              className="p-4 rounded-lg bg-slate-900/60 border border-slate-800 space-y-3"
            >
              <div className="flex items-start justify-between gap-2">
                <div>
                  <h3 className="text-sm font-bold text-slate-100">{rule.name}</h3>
                  <p className="text-slate-400 text-[11px] mt-0.5">{rule.description}</p>
                </div>
                <StatusBadge status={rule.severity} />
              </div>

              <div className="grid grid-cols-2 gap-2 p-3 rounded bg-slate-950 border border-slate-800 text-[11px]">
                <div>
                  <span className="text-slate-500">Signal Type:</span>
                  <div className="text-cyan-400 font-bold">{rule.rule_type}</div>
                </div>
                <div>
                  <span className="text-slate-500">Trigger Threshold:</span>
                  <div className="text-amber-400 font-bold">
                    {rule.condition} {rule.threshold}
                  </div>
                </div>
                <div>
                  <span className="text-slate-500">Risk Weight:</span>
                  <div className="text-slate-200">+{rule.weight} pts</div>
                </div>
                <div>
                  <span className="text-slate-500">Action:</span>
                  <div className={rule.action === 'QUARANTINE' ? 'text-red-400 font-bold' : 'text-slate-200'}>
                    {rule.action}
                  </div>
                </div>
              </div>
            </div>
          ))
        ) : (
          <div className="col-span-2 p-8 text-center text-slate-500 rounded-lg bg-slate-900/40 border border-slate-800">
            No custom rules defined. Active default heuristics are enforced by the engine.
          </div>
        )}
      </div>

      {/* Add Rule Modal */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm">
          <form
            onSubmit={handleCreateRule}
            className="bg-slate-900 border border-slate-800 rounded-lg max-w-md w-full p-6 space-y-4 font-mono text-xs"
          >
            <h3 className="text-sm font-bold text-slate-100 flex items-center gap-2">
              <Sliders className="w-4 h-4 text-cyan-400" />
              Configure New Threat Rule
            </h3>

            <div>
              <label className="block text-slate-400 mb-1">Rule Name:</label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="e.g. Mass File Rename Guard"
                required
                className="w-full bg-slate-950 border border-slate-800 rounded p-2 text-slate-200 focus:outline-none focus:border-cyan-500"
              />
            </div>

            <div>
              <label className="block text-slate-400 mb-1">Description:</label>
              <input
                type="text"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="e.g. Flags rapid extension changing"
                required
                className="w-full bg-slate-950 border border-slate-800 rounded p-2 text-slate-200 focus:outline-none focus:border-cyan-500"
              />
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-slate-400 mb-1">Signal Type:</label>
                <select
                  value={ruleType}
                  onChange={(e) => setRuleType(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded p-2 text-slate-200 focus:outline-none focus:border-cyan-500"
                >
                  <option value="ENTROPY">Entropy (0.0-8.0)</option>
                  <option value="RENAME_RATE">Rename Rate (/min)</option>
                  <option value="WRITE_RATE">Write Rate (/min)</option>
                  <option value="DELETE_RATE">Delete Rate (/min)</option>
                  <option value="CANARY">Canary Tripwire</option>
                  <option value="PROCESS">Process I/O Anomaly</option>
                  <option value="YARA">YARA Signature</option>
                </select>
              </div>

              <div>
                <label className="block text-slate-400 mb-1">Threshold:</label>
                <input
                  type="number"
                  step="0.1"
                  value={threshold}
                  onChange={(e) => setThreshold(e.target.value)}
                  required
                  className="w-full bg-slate-950 border border-slate-800 rounded p-2 text-slate-200 focus:outline-none focus:border-cyan-500"
                />
              </div>
            </div>

            <div className="grid grid-cols-3 gap-3">
              <div>
                <label className="block text-slate-400 mb-1">Score Weight:</label>
                <input
                  type="number"
                  value={weight}
                  onChange={(e) => setWeight(e.target.value)}
                  required
                  className="w-full bg-slate-950 border border-slate-800 rounded p-2 text-slate-200 focus:outline-none focus:border-cyan-500"
                />
              </div>

              <div>
                <label className="block text-slate-400 mb-1">Severity:</label>
                <select
                  value={severity}
                  onChange={(e) => setSeverity(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded p-2 text-slate-200 focus:outline-none focus:border-cyan-500"
                >
                  <option value="CRITICAL">Critical</option>
                  <option value="HIGH">High</option>
                  <option value="MEDIUM">Medium</option>
                  <option value="LOW">Low</option>
                </select>
              </div>

              <div>
                <label className="block text-slate-400 mb-1">Action:</label>
                <select
                  value={action}
                  onChange={(e) => setAction(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded p-2 text-slate-200 focus:outline-none focus:border-cyan-500"
                >
                  <option value="ALERT">Alert Only</option>
                  <option value="QUARANTINE">Quarantine Endpoint</option>
                </select>
              </div>
            </div>

            <div className="flex justify-end gap-2 pt-2 border-t border-slate-800">
              <button
                type="button"
                onClick={() => setIsModalOpen(false)}
                className="px-3 py-1.5 rounded bg-slate-800 text-slate-300 hover:bg-slate-700"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={createRuleMutation.isPending}
                className="px-3 py-1.5 rounded bg-cyan-600 hover:bg-cyan-500 text-white font-semibold"
              >
                Save Rule
              </button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
};


import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { History, ArrowRight, Search } from 'lucide-react';
import { backupService } from '../services/backupService';

export const VersionHistory: React.FC = () => {
  const [selectedFileId, setSelectedFileId] = useState<string>('');

  const { data: snapshotsData, isLoading: listLoading } = useQuery({
    queryKey: ['backups-list-for-history'],
    queryFn: () => backupService.listBackups(undefined, 0, 100),
  });

  const { data: fileHistory, isLoading: historyLoading } = useQuery({
    queryKey: ['file-history', selectedFileId],
    queryFn: () => backupService.getFileHistory(selectedFileId),
    enabled: !!selectedFileId,
  });

  // Unique files from snapshots list
  const uniqueFiles = Array.from(
    new Map(
      (snapshotsData?.items ?? []).map((s) => [s.file_id, { id: s.file_id, path: s.file_path, name: s.original_filename }])
    ).values()
  );

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="pb-4 border-b border-slate-800">
        <h1 className="text-xl font-bold tracking-tight text-slate-100 font-mono flex items-center gap-2">
          <History className="w-5 h-5 text-cyan-400" />
          IMMUTABLE VERSION HISTORY & AUDIT TRAIL
        </h1>
        <p className="text-xs text-slate-400 mt-1">
          Detailed version lineage, cryptographic digests, and tamper-proof snapshot timelines for individual files
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left pane: File Selector */}
        <div className="cyber-card p-4 flex flex-col h-[600px]">
          <div className="pb-3 border-b border-slate-800 mb-3">
            <h3 className="text-xs font-semibold text-slate-200 font-mono uppercase tracking-wider">
              Protected Files ({uniqueFiles.length})
            </h3>
          </div>

          <div className="overflow-y-auto space-y-1.5 flex-1 pr-1">
            {listLoading ? (
              <p className="text-xs text-slate-500 py-4 text-center">Loading protected files...</p>
            ) : uniqueFiles.length === 0 ? (
              <p className="text-xs text-slate-500 py-4 text-center">No backed up files found yet.</p>
            ) : (
              uniqueFiles.map((f) => (
                <button
                  key={f.id}
                  onClick={() => setSelectedFileId(f.id)}
                  className={`w-full text-left p-2.5 rounded-lg border transition-all text-xs font-mono flex items-center justify-between ${
                    selectedFileId === f.id
                      ? 'bg-cyan-500/10 border-cyan-500/40 text-cyan-300'
                      : 'bg-slate-900/40 border-slate-800/80 text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
                  }`}
                >
                  <div className="truncate mr-2">
                    <p className="font-semibold text-slate-200 truncate">{f.name}</p>
                    <p className="text-[10px] text-slate-500 truncate">{f.path}</p>
                  </div>
                  <ArrowRight className="w-3.5 h-3.5 shrink-0" />
                </button>
              ))
            )}
          </div>
        </div>

        {/* Right pane: Version History Timeline */}
        <div className="cyber-card p-6 lg:col-span-2 min-h-[600px] flex flex-col">
          {!selectedFileId ? (
            <div className="flex-1 flex flex-col items-center justify-center text-center p-8 text-slate-500">
              <Search className="w-10 h-10 mb-3 text-slate-600" />
              <h3 className="text-sm font-semibold text-slate-300">No File Selected</h3>
              <p className="text-xs text-slate-500 mt-1 max-w-sm">
                Select a protected file from the left sidebar to inspect its immutable version history, SHA-256 integrity, and encryption metadata.
              </p>
            </div>
          ) : historyLoading ? (
            <div className="flex-1 flex items-center justify-center">
              <span className="text-xs font-mono text-cyan-400 animate-pulse">Loading version timeline...</span>
            </div>
          ) : !fileHistory ? (
            <p className="text-xs text-red-400">File record not found.</p>
          ) : (
            <div className="space-y-4">
              <div className="pb-4 border-b border-slate-800 flex items-center justify-between">
                <div>
                  <h2 className="text-base font-bold text-slate-100 font-mono">{fileHistory.original_filename}</h2>
                  <p className="text-xs text-slate-400 font-mono mt-0.5 truncate max-w-md">{fileHistory.file_path}</p>
                </div>
                <div className="text-right">
                  <span className="text-xs font-mono text-cyan-400 bg-cyan-500/10 px-2.5 py-1 rounded border border-cyan-500/20">
                    {fileHistory.versions.length} Total Versions
                  </span>
                </div>
              </div>

              {/* Version List */}
              <div className="space-y-3 overflow-y-auto max-h-[460px] pr-2">
                {fileHistory.versions.map((ver, idx) => (
                  <div
                    key={ver.id}
                    className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 hover:border-slate-700 transition-all font-mono text-xs space-y-2"
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <span className="px-2 py-0.5 rounded bg-cyan-500/20 text-cyan-300 border border-cyan-500/30 font-bold">
                          Version {ver.version_number}
                        </span>
                        {idx === 0 && (
                          <span className="px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 text-[10px]">
                            LATEST SNAPSHOT
                          </span>
                        )}
                      </div>
                      <span className="text-slate-500 text-[11px]">
                        {new Date(ver.created_at).toLocaleString()}
                      </span>
                    </div>

                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 pt-2 border-t border-slate-800/60 text-[11px]">
                      <div>
                        <span className="text-slate-500 block">Original Size</span>
                        <span className="text-slate-300 font-semibold">
                          {(ver.original_size_bytes / 1024).toFixed(1)} KB
                        </span>
                      </div>
                      <div>
                        <span className="text-slate-500 block">Encrypted Size</span>
                        <span className="text-emerald-400 font-semibold">
                          {(ver.size_bytes / 1024).toFixed(1)} KB
                        </span>
                      </div>
                      <div>
                        <span className="text-slate-500 block">Algorithm</span>
                        <span className="text-cyan-400 font-semibold">{ver.encryption_algorithm}</span>
                      </div>
                      <div>
                        <span className="text-slate-500 block">Compression</span>
                        <span className="text-slate-300 font-semibold">{ver.compression_algorithm}</span>
                      </div>
                    </div>

                    <div className="p-2 rounded bg-slate-950 border border-slate-800/80 text-[11px] text-slate-400 space-y-1">
                      <div className="truncate">
                        <span className="text-slate-500">SHA-256 Digest: </span>
                        <span className="text-slate-300">{ver.file_hash_sha256}</span>
                      </div>
                      <div className="truncate text-slate-500">
                        <span>Object: </span>
                        <span>{ver.storage_path}</span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};


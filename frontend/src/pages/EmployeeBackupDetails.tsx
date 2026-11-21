import React, { useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import {
  ArrowLeft,
  CalendarClock,
  FileClock,
  FileText,
  HardDrive,
  ShieldCheck,
  Users,
} from 'lucide-react';
import { MetricCard } from '../components/widgets/MetricCard';
import { backupService } from '../services/backupService';

const FILE_PAGE_SIZE = 20;
const RECOVERY_PAGE_SIZE = 20;

const formatBytes = (bytes: number) => {
  if (bytes < 1024) return `${bytes} B`;
  const units = ['KB', 'MB', 'GB', 'TB'];
  let value = bytes / 1024;
  let unitIndex = 0;
  while (value >= 1024 && unitIndex < units.length - 1) {
    value /= 1024;
    unitIndex += 1;
  }
  return `${value.toFixed(1)} ${units[unitIndex]}`;
};

const formatDate = (date?: string | null) =>
  date ? new Date(date).toLocaleString() : 'Never';

const getFileType = (fileName: string) => {
  const extension = fileName.split('.').pop();
  return extension && extension !== fileName ? extension.toUpperCase() : 'FILE';
};

export const EmployeeBackupDetails: React.FC = () => {
  const { employeeId } = useParams<{ employeeId: string }>();
  const [fileSkip, setFileSkip] = useState(0);
  const [recoverySkip, setRecoverySkip] = useState(0);

  const {
    data,
    isLoading,
    isError,
    error,
  } = useQuery({
    queryKey: ['employee-backup-details', employeeId, fileSkip, recoverySkip],
    queryFn: () =>
      backupService.getEmployeeBackupDetails(
        employeeId!,
        fileSkip,
        FILE_PAGE_SIZE,
        recoverySkip,
        RECOVERY_PAGE_SIZE
      ),
    enabled: Boolean(employeeId),
  });

  if (isLoading) {
    return (
      <div className="py-16 text-center text-slate-500 font-mono text-xs">
        <FileClock className="w-6 h-6 animate-pulse mx-auto mb-2 text-cyan-400" />
        Loading employee backup details...
      </div>
    );
  }

  if (isError || !data) {
    return (
      <div className="space-y-5">
        <Link
          to="/backups?scope=employees"
          className="inline-flex items-center gap-2 text-sm text-cyan-300 hover:text-cyan-200"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to Employees
        </Link>
        <div role="alert" className="p-5 rounded-lg border border-red-500/30 bg-red-500/10 text-red-300">
          {error instanceof Error ? error.message : 'Unable to load employee backup details.'}
        </div>
      </div>
    );
  }

  const employee = data.employee;
  const filePage = data.files;
  const recoveryPage = data.recovery_history;

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex flex-col gap-4 border-b border-slate-800 pb-4">
        <Link
          to="/backups?scope=employees"
          className="inline-flex w-fit items-center gap-2 text-xs font-mono text-cyan-300 hover:text-cyan-200"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to Employees
        </Link>
        <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4">
          <div>
            <h1 className="flex items-center gap-2 text-xl font-bold tracking-tight text-slate-100 font-mono">
              <Users className="w-5 h-5 text-cyan-400" />
              {employee.full_name} · EMPLOYEE BACKUPS
            </h1>
            <p className="mt-1 text-xs text-slate-400">{employee.email}</p>
            <p className="mt-1 text-[11px] text-slate-500 font-mono">
              Employee ID: {employee.id} · Member since {new Date(employee.created_at).toLocaleDateString()} · {employee.is_active ? 'ACTIVE' : 'INACTIVE'}
            </p>
          </div>
          <span className="inline-flex h-fit items-center gap-2 rounded border border-amber-500/30 bg-amber-500/10 px-3 py-2 text-[11px] font-mono text-amber-300">
            <ShieldCheck className="w-4 h-4" />
            READ-ONLY · Employee files cannot be changed or restored
          </span>
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard
          title="Backup Files"
          value={data.total_backup_files}
          subtitle="Owned by this employee"
          icon={FileText}
          variant="cyan"
        />
        <MetricCard
          title="Encrypted Storage"
          value={formatBytes(data.storage_used_bytes)}
          subtitle="Across all stored versions"
          icon={HardDrive}
          variant="emerald"
        />
        <MetricCard
          title="Last Backup"
          value={data.last_backup_at ? new Date(data.last_backup_at).toLocaleDateString() : 'Never'}
          subtitle={formatDate(data.last_backup_at)}
          icon={CalendarClock}
          variant="cyan"
        />
        <MetricCard
          title="Backup Status"
          value={data.backup_status.replace(/_/g, ' ')}
          subtitle="Latest backup run"
          icon={ShieldCheck}
          variant="emerald"
        />
      </div>

      <section className="cyber-card overflow-hidden">
        <div className="flex items-center justify-between border-b border-slate-800 px-6 py-4">
          <div>
            <h2 className="text-sm font-semibold text-slate-200 font-mono">Employee Backup Files</h2>
            <p className="mt-1 text-xs text-slate-500">File metadata and immutable version history. No restore or modification actions are available.</p>
          </div>
          <span className="text-xs font-mono text-cyan-300">{filePage.total} files</span>
        </div>
        {!filePage.items.length ? (
          <div className="py-14 text-center text-sm text-slate-400">This employee has no backup files.</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="border-b border-slate-800 bg-slate-900/40 text-slate-400 font-mono">
                  <th className="px-4 py-3 font-medium">File</th>
                  <th className="px-4 py-3 font-medium">Type</th>
                  <th className="px-4 py-3 font-medium">Size</th>
                  <th className="px-4 py-3 font-medium">Versions</th>
                  <th className="px-4 py-3 font-medium">Latest Backup</th>
                  <th className="px-4 py-3 font-medium">History</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {filePage.items.map((file) => (
                  <tr key={file.id} className="align-top hover:bg-slate-800/30">
                    <td className="px-4 py-3">
                      <div className="font-semibold text-slate-200">{file.original_filename}</div>
                      <div className="mt-1 max-w-md truncate font-mono text-[10px] text-slate-500" title={file.file_path}>{file.file_path}</div>
                      {file.is_deleted && <div className="mt-1 text-[10px] text-amber-400">Deleted from source · backup history retained</div>}
                    </td>
                    <td className="px-4 py-3 text-slate-400">{getFileType(file.original_filename)}</td>
                    <td className="px-4 py-3 text-slate-300">{formatBytes(file.file_size)}</td>
                    <td className="px-4 py-3 text-cyan-300">{file.total_versions}</td>
                    <td className="px-4 py-3 text-slate-400">{formatDate(file.versions[file.versions.length - 1]?.created_at ?? file.updated_at)}</td>
                    <td className="px-4 py-3">
                      {file.versions.length ? (
                        <details className="min-w-60">
                          <summary className="cursor-pointer text-cyan-300 hover:text-cyan-200">
                            View {file.versions.length} version{file.versions.length === 1 ? '' : 's'}
                          </summary>
                          <div className="mt-2 space-y-2 border-l border-slate-700 pl-3">
                            {file.versions.map((version) => (
                              <div key={version.id} className="text-[10px] text-slate-400">
                                <div className="font-mono text-slate-300">v{version.version_number} · {formatDate(version.created_at)}</div>
                                <div>{formatBytes(version.original_size_bytes)} original · {formatBytes(version.encrypted_size_bytes)} encrypted</div>
                                <div className="font-mono" title={version.file_hash_sha256}>SHA-256 {version.file_hash_sha256.slice(0, 16)}...</div>
                              </div>
                            ))}
                          </div>
                        </details>
                      ) : (
                        <span className="text-slate-500">No version history</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        {filePage.total > FILE_PAGE_SIZE && (
          <div className="flex items-center justify-between border-t border-slate-800 px-6 py-3 text-xs">
            <span className="text-slate-500">Showing {filePage.skip + 1}–{Math.min(filePage.skip + filePage.items.length, filePage.total)} of {filePage.total}</span>
            <div className="flex gap-2">
              <button
                type="button"
                disabled={fileSkip === 0}
                onClick={() => setFileSkip(Math.max(0, fileSkip - FILE_PAGE_SIZE))}
                className="rounded border border-slate-700 px-3 py-1 text-slate-300 disabled:opacity-40"
              >
                Previous
              </button>
              <button
                type="button"
                disabled={fileSkip + FILE_PAGE_SIZE >= filePage.total}
                onClick={() => setFileSkip(fileSkip + FILE_PAGE_SIZE)}
                className="rounded border border-slate-700 px-3 py-1 text-slate-300 disabled:opacity-40"
              >
                Next
              </button>
            </div>
          </div>
        )}
      </section>

      <section className="cyber-card overflow-hidden">
        <div className="flex items-center justify-between border-b border-slate-800 px-6 py-4">
          <div>
            <h2 className="text-sm font-semibold text-slate-200 font-mono">Recovery History</h2>
            <p className="mt-1 text-xs text-slate-500">Read-only job status and outcome metadata for this employee.</p>
          </div>
          <span className="text-xs font-mono text-cyan-300">{recoveryPage.total} jobs</span>
        </div>
        {!recoveryPage.items.length ? (
          <div className="py-12 text-center text-sm text-slate-400">No recovery jobs found for this employee.</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="border-b border-slate-800 bg-slate-900/40 text-slate-400 font-mono">
                  <th className="px-4 py-3 font-medium">Created</th>
                  <th className="px-4 py-3 font-medium">Type</th>
                  <th className="px-4 py-3 font-medium">Status</th>
                  <th className="px-4 py-3 font-medium">Files</th>
                  <th className="px-4 py-3 font-medium">Restored</th>
                  <th className="px-4 py-3 font-medium">Failed</th>
                  <th className="px-4 py-3 font-medium">Bytes Restored</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {recoveryPage.items.map((job) => (
                  <tr key={job.id} className="hover:bg-slate-800/30">
                    <td className="px-4 py-3 text-slate-400">{formatDate(job.created_at)}</td>
                    <td className="px-4 py-3 text-slate-300">{job.job_type.replace(/_/g, ' ')}</td>
                    <td className="px-4 py-3">
                      <span className="rounded border border-slate-700 bg-slate-800 px-2 py-1 font-mono text-[10px] text-slate-300">{job.status}</span>
                    </td>
                    <td className="px-4 py-3 text-slate-300">{job.total_files}</td>
                    <td className="px-4 py-3 text-emerald-300">{job.files_restored}</td>
                    <td className="px-4 py-3 text-red-300">{job.files_failed}</td>
                    <td className="px-4 py-3 text-slate-400">{formatBytes(job.bytes_restored)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        {recoveryPage.total > RECOVERY_PAGE_SIZE && (
          <div className="flex items-center justify-between border-t border-slate-800 px-6 py-3 text-xs">
            <span className="text-slate-500">Showing {recoveryPage.skip + 1}–{Math.min(recoveryPage.skip + recoveryPage.items.length, recoveryPage.total)} of {recoveryPage.total}</span>
            <div className="flex gap-2">
              <button
                type="button"
                disabled={recoverySkip === 0}
                onClick={() => setRecoverySkip(Math.max(0, recoverySkip - RECOVERY_PAGE_SIZE))}
                className="rounded border border-slate-700 px-3 py-1 text-slate-300 disabled:opacity-40"
              >
                Previous
              </button>
              <button
                type="button"
                disabled={recoverySkip + RECOVERY_PAGE_SIZE >= recoveryPage.total}
                onClick={() => setRecoverySkip(recoverySkip + RECOVERY_PAGE_SIZE)}
                className="rounded border border-slate-700 px-3 py-1 text-slate-300 disabled:opacity-40"
              >
                Next
              </button>
            </div>
          </div>
        )}
      </section>
    </div>
  );
};

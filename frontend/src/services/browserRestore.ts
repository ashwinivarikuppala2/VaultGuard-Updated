import { OverwritePolicy, RecoveryJobItem, RecoveryJobType } from '../types';

export interface RestoreWritable {
  write(data: Blob): Promise<void>;
  close(): Promise<void>;
  abort?(): Promise<void>;
}

export interface RestoreFileHandle {
  createWritable(): Promise<RestoreWritable>;
}

export interface RestoreDirectoryHandle {
  /** The name of the selected folder as reported by the browser. */
  readonly name?: string;
  getFileHandle(name: string, options?: { create?: boolean }): Promise<RestoreFileHandle>;
  getDirectoryHandle(name: string, options?: { create?: boolean }): Promise<RestoreDirectoryHandle>;
}

export type BrowserRestoreItem = RecoveryJobItem;

const normalizeSegments = (path: string): string[] => {
  if (path.includes('\0')) {
    throw new Error('A restored file path contains an invalid null byte.');
  }

  const withoutDrive = path.replace(/^[a-zA-Z]:/, '').replace(/\\/g, '/').replace(/^\/+/, '');
  const segments = withoutDrive.split('/').filter((segment) => segment && segment !== '.');
  if (!segments.length || segments.some((segment) => segment === '..')) {
    throw new Error('A restored file path is not a safe relative path.');
  }
  return segments;
};

const getRestorePath = (
  item: BrowserRestoreItem,
  jobType: RecoveryJobType,
  folderPath?: string
): string[] => {
  const originalSegments = normalizeSegments(item.original_path);
  if (jobType !== 'FOLDER' || !folderPath) {
    return [originalSegments[originalSegments.length - 1]];
  }

  const rootSegments = normalizeSegments(folderPath);
  const matchesRoot = rootSegments.every(
    (segment, index) => originalSegments[index]?.toLowerCase() === segment.toLowerCase()
  );
  return matchesRoot && originalSegments.length > rootSegments.length
    ? originalSegments.slice(rootSegments.length)
    : [originalSegments[originalSegments.length - 1]];
};

const fileExists = async (directory: RestoreDirectoryHandle, name: string): Promise<boolean> => {
  try {
    await directory.getFileHandle(name);
    return true;
  } catch (error) {
    if (error instanceof DOMException && error.name === 'NotFoundError') {
      return false;
    }
    throw error;
  }
};

const renamedFileName = (name: string, index: number): string => {
  const dot = name.lastIndexOf('.');
  const stem = dot > 0 ? name.slice(0, dot) : name;
  const extension = dot > 0 ? name.slice(dot) : '';
  return `${stem} (${index})${extension}`;
};

export async function writeRestoredFiles(
  directory: RestoreDirectoryHandle,
  items: BrowserRestoreItem[],
  loadFile: (item: BrowserRestoreItem) => Promise<Blob>,
  overwritePolicy: OverwritePolicy,
  confirmOverwrite: (fileNames: string[]) => boolean,
  jobType: RecoveryJobType,
  folderPath?: string
): Promise<{ written: number; skipped: number }> {
  const completedItems = items.filter((item) => item.status === 'COMPLETED');
  if (completedItems.some((item) => !item.sha256_verified)) {
    throw new Error('Only completed, integrity-verified restore files can be written to your folder.');
  }
  const prepared = completedItems.map((item) => ({ item, path: getRestorePath(item, jobType, folderPath) }));

  const destinations: Array<{ item: BrowserRestoreItem; directory: RestoreDirectoryHandle; name: string }> = [];
  const reservedPaths = new Set<string>();
  let skipped = items.filter((item) => item.status === 'SKIPPED').length;
  const overwrites: string[] = [];

  for (const { item, path } of prepared) {
    let targetDirectory = directory;
    for (const segment of path.slice(0, -1)) {
      targetDirectory = await targetDirectory.getDirectoryHandle(segment, { create: true });
    }

    let name = path[path.length - 1];
    const getPathKey = (fileName: string) => [...path.slice(0, -1), fileName].join('/');
    let exists = (await fileExists(targetDirectory, name)) || reservedPaths.has(getPathKey(name));
    if (exists && overwritePolicy === 'SKIP') {
      skipped += 1;
      continue;
    }
    if (exists && overwritePolicy === 'RENAME') {
      let index = 1;
      do {
        name = renamedFileName(path[path.length - 1], index++);
        exists = (await fileExists(targetDirectory, name)) || reservedPaths.has(getPathKey(name));
      } while (exists);
    } else if (exists && overwritePolicy === 'OVERWRITE') {
      overwrites.push(path.join('/'));
    }
    destinations.push({ item, directory: targetDirectory, name });
    reservedPaths.add(getPathKey(name));
  }

  if (overwrites.length && !confirmOverwrite(overwrites)) {
    throw new Error('Restore cancelled because overwrite confirmation was declined.');
  }

  for (const { item, directory: targetDirectory, name } of destinations) {
    const fileHandle = await targetDirectory.getFileHandle(name, { create: true });
    const writable = await fileHandle.createWritable();
    try {
      const blob = await loadFile(item);
      await writable.write(blob);
      await writable.close();
    } catch (error) {
      // Always abort the writable on any failure to release the file handle and
      // prevent a half-written file from remaining on disk.
      try {
        if (typeof writable.abort === 'function') {
          await writable.abort();
        } else {
          await writable.close();
        }
      } catch {
        // Ignore secondary abort/close errors — the original error is re-thrown below.
      }
      throw error;
    }
  }

  return { written: destinations.length, skipped };
}

export function getDirectoryPicker(): ((options: { mode: 'readwrite' }) => Promise<RestoreDirectoryHandle>) | undefined {
  const picker = (window as Window & {
    showDirectoryPicker?: (options: { mode: 'readwrite' }) => Promise<RestoreDirectoryHandle>;
  }).showDirectoryPicker;
  // Call without .call() to preserve native browser invocation context required by
  // the File System Access API security model (must be a direct user-gesture call).
  return picker ? (options) => picker.call(window, options) : undefined;
}

import { describe, expect, it, vi } from 'vitest';
import { BrowserRestoreItem, RestoreDirectoryHandle, RestoreWritable, writeRestoredFiles } from '../services/browserRestore';

type TestFile = {
  content: Blob;
  abortCalled: boolean;
  createWritable: () => Promise<RestoreWritable>;
};

type TestDirectory = {
  handle: RestoreDirectoryHandle;
  files: Map<string, TestFile>;
  directories: Map<string, TestDirectory>;
};

const makeDirectory = (): TestDirectory => {
  const files = new Map<string, TestFile>();
  const directories = new Map<string, TestDirectory>();
  const handle: RestoreDirectoryHandle = {
    async getFileHandle(name, options) {
      let file = files.get(name);
      if (!file && !options?.create) {
        throw new DOMException('File not found', 'NotFoundError');
      }
      if (!file) {
        file = {
          content: new Blob(),
          abortCalled: false,
          async createWritable() {
            let pending = new Blob();
            const f = file!;
            return {
              async write(blob) {
                pending = blob;
              },
              async close() {
                f.content = pending;
              },
              async abort() {
                f.abortCalled = true;
              },
            };
          },
        };
        files.set(name, file);
      }
      return file;
    },
    async getDirectoryHandle(name, options) {
      let directory = directories.get(name);
      if (!directory && !options?.create) {
        throw new DOMException('Directory not found', 'NotFoundError');
      }
      if (!directory) {
        directory = makeDirectory();
        directories.set(name, directory);
      }
      return directory.handle;
    },
  };
  return { handle, files, directories };
};

const verifiedItem: BrowserRestoreItem = {
  id: 'item-1',
  recovery_job_id: 'job-1',
  file_id: 'file-1',
  file_version_id: 'version-1',
  original_path: 'C:\\Users\\Employee\\Documents\\Reports\\quarterly.txt',
  target_path: 'server-safe-root\\quarterly.txt',
  status: 'COMPLETED',
  bytes_restored: 8,
  sha256_verified: true,
  threat_status: 'no known threat detected',
  created_at: '',
  updated_at: '',
};

describe('browser restore destination', () => {
  it('writes verified restored bytes into the employee-selected folder', async () => {
    const selectedFolder = makeDirectory();
    const loadFile = vi.fn(async () => new Blob(['restored']));

    const result = await writeRestoredFiles(
      selectedFolder.handle,
      [verifiedItem],
      loadFile,
      'SKIP',
      () => true,
      'FOLDER',
      'C:\\Users\\Employee\\Documents'
    );

    const reports = selectedFolder.directories.get('Reports');
    expect(result).toEqual({ written: 1, skipped: 0 });
    expect(reports?.files.get('quarterly.txt')).toBeDefined();
    expect(await reports?.files.get('quarterly.txt')?.content.text()).toBe('restored');
    expect(loadFile).toHaveBeenCalledWith(verifiedItem);
  });

  it('requires confirmation before overwriting an existing file', async () => {
    const selectedFolder = makeDirectory();
    const existing = await selectedFolder.handle.getFileHandle('quarterly.txt', { create: true });
    const writable = await existing.createWritable();
    await writable.write(new Blob(['keep this']));
    await writable.close();

    await expect(writeRestoredFiles(
      selectedFolder.handle,
      [{ ...verifiedItem, original_path: 'quarterly.txt' }],
      async () => new Blob(['replace']),
      'OVERWRITE',
      () => false,
      'SINGLE_FILE'
    )).rejects.toThrow('Restore cancelled');

    const file = await selectedFolder.handle.getFileHandle('quarterly.txt');
    expect(await (file as TestFile).content.text()).toBe('keep this');
  });

  it('renames a restored file when rename collision handling is selected', async () => {
    const selectedFolder = makeDirectory();
    const existing = await selectedFolder.handle.getFileHandle('quarterly.txt', { create: true });
    const existingWritable = await existing.createWritable();
    await existingWritable.write(new Blob(['existing']));
    await existingWritable.close();

    await writeRestoredFiles(
      selectedFolder.handle,
      [{ ...verifiedItem, original_path: 'quarterly.txt' }],
      async () => new Blob(['restored']),
      'RENAME',
      () => true,
      'SINGLE_FILE'
    );

    const renamed = await selectedFolder.handle.getFileHandle('quarterly (1).txt');
    expect(await (renamed as TestFile).content.text()).toBe('restored');
  });

  it('handles name collisions between files in the same restore job', async () => {
    const selectedFolder = makeDirectory();
    const secondItem = { ...verifiedItem, id: 'item-2', original_path: 'D:\\Archive\\quarterly.txt' };

    await writeRestoredFiles(
      selectedFolder.handle,
      [verifiedItem, secondItem],
      async (item) => new Blob([item.id]),
      'RENAME',
      () => true,
      'BULK'
    );

    const original = await selectedFolder.handle.getFileHandle('quarterly.txt');
    const renamed = await selectedFolder.handle.getFileHandle('quarterly (1).txt');
    expect(await (original as TestFile).content.text()).toBe('item-1');
    expect(await (renamed as TestFile).content.text()).toBe('item-2');
  });

  it('aborts the writable and propagates the error when loadFile throws during the write', async () => {
    const selectedFolder = makeDirectory();
    const networkError = new Error('Network failure: download interrupted');

    await expect(writeRestoredFiles(
      selectedFolder.handle,
      [verifiedItem],
      async () => { throw networkError; },
      'SKIP',
      () => true,
      'SINGLE_FILE'
    )).rejects.toThrow('Network failure: download interrupted');

    // The file handle was created but abort() should have been called on its writable.
    const file = selectedFolder.files.get('quarterly.txt') as TestFile | undefined;
    expect(file?.abortCalled).toBe(true);
    // Content must remain empty because the write was aborted before close().
    if (file) {
      expect(await file.content.text()).toBe('');
    }
  });

  it('skips items whose status is not COMPLETED', async () => {
    const selectedFolder = makeDirectory();
    const skippedItem: BrowserRestoreItem = { ...verifiedItem, id: 'item-skip', status: 'SKIPPED' };

    const result = await writeRestoredFiles(
      selectedFolder.handle,
      [skippedItem],
      vi.fn(async () => new Blob(['should not write'])),
      'SKIP',
      () => true,
      'SINGLE_FILE'
    );

    expect(result.written).toBe(0);
    expect(result.skipped).toBe(1);
  });

  it('rejects unverified items and does not write anything', async () => {
    const selectedFolder = makeDirectory();
    const unverifiedItem: BrowserRestoreItem = { ...verifiedItem, sha256_verified: false };

    await expect(writeRestoredFiles(
      selectedFolder.handle,
      [unverifiedItem],
      async () => new Blob(['unsafe']),
      'SKIP',
      () => true,
      'SINGLE_FILE'
    )).rejects.toThrow('Only completed, integrity-verified restore files');

    expect(selectedFolder.files.size).toBe(0);
  });
});

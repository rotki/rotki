// @vitest-environment node
import type { AppConfig } from '@electron/main/app-config';
import type { LogService } from '@electron/main/log-service';
import { createMock } from '@test/utils/create-mock';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { UpdateHandlers } from './update-handlers';

const { autoUpdater } = await vi.hoisted(async () => {
  const { EventEmitter } = await import('node:events');
  return {
    autoUpdater: Object.assign(new EventEmitter(), {
      autoDownload: true,
      logger: null,
      checkForUpdates: vi.fn<() => Promise<unknown>>(),
    }),
  };
});

vi.mock('electron-updater', () => ({ default: { autoUpdater } }));

/**
 * The seam: `checkForUpdates` resolves whether an update exists, and a failed check resolves
 * false and is logged once and briefly. electron-updater emits the failure as an `error` event and
 * also rejects with it, and its message holds the whole release feed, so logging the raw error from
 * both paths put thousands of lines of release notes in the log per failed check.
 */
describe('updateHandlers.checkForUpdates', () => {
  afterEach(() => {
    autoUpdater.removeAllListeners();
    autoUpdater.checkForUpdates.mockReset();
  });

  it('should log a failed check once with only the first line of the error', async () => {
    const logError = vi.fn<(message?: unknown) => void>();
    const logger = createMock<LogService>({ error: logError });
    const error = new Error('Cannot parse releases feed: HttpError: 504\nData:\n<li>release notes</li>');
    autoUpdater.checkForUpdates.mockImplementation(async () => {
      autoUpdater.emit('error', error);
      throw error;
    });

    const result = await new UpdateHandlers(logger, createMock<AppConfig>({ isDev: false })).checkForUpdates();

    expect(result).toBe(false);
    expect(logError).toHaveBeenCalledOnce();
    expect(logError).toHaveBeenCalledWith('Update check failed: Cannot parse releases feed: HttpError: 504 (details truncated)');
  });

  it('should resolve true when an update is available', async () => {
    const logError = vi.fn<(message?: unknown) => void>();
    const logger = createMock<LogService>({ error: logError });
    autoUpdater.checkForUpdates.mockImplementation(async () => {
      autoUpdater.emit('update-available');
      return null;
    });

    const result = await new UpdateHandlers(logger, createMock<AppConfig>({ isDev: false })).checkForUpdates();

    expect(result).toBe(true);
    expect(logError).not.toHaveBeenCalled();
  });
});

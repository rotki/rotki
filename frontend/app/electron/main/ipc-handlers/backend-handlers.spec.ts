import type { LogService } from '@electron/main/log-service';
import { createMock } from '@test/utils/create-mock';
import { describe, expect, it, vi } from 'vitest';
import { BackendHandlers } from './backend-handlers';

function makeLogger(): LogService {
  return createMock<LogService>();
}

describe('backendHandlers', () => {
  it('should run restartSubprocesses and report success', async () => {
    const restartSubprocesses = vi.fn(async (): Promise<void> => {});
    const handlers = new BackendHandlers(makeLogger());
    handlers.initialize({ restartSubprocesses, sendIpcMessage: vi.fn() });

    const ok = await handlers.restartBackend({ logFromOtherModules: true });

    expect(ok).toBe(true);
    expect(restartSubprocesses).toHaveBeenCalledWith({ logFromOtherModules: true });
  });

  it('should report failure when restartSubprocesses throws', async () => {
    const restartSubprocesses = vi.fn(async (): Promise<void> => {
      throw new Error('boom');
    });
    const handlers = new BackendHandlers(makeLogger());
    handlers.initialize({ restartSubprocesses, sendIpcMessage: vi.fn() });

    const ok = await handlers.restartBackend({});

    expect(ok).toBe(false);
  });

  it('should ignore a re-entrant restart while one is already in flight', async () => {
    let release: () => void = () => {};
    const gate = new Promise<void>((resolve) => {
      release = resolve;
    });
    const restartSubprocesses = vi.fn(async (): Promise<void> => {
      await gate;
    });
    const handlers = new BackendHandlers(makeLogger());
    handlers.initialize({ restartSubprocesses, sendIpcMessage: vi.fn() });

    const first = handlers.restartBackend({});
    const second = await handlers.restartBackend({}); // in-flight → returns false without re-running

    expect(second).toBe(false);
    expect(restartSubprocesses).toHaveBeenCalledTimes(1);

    release();
    expect(await first).toBe(true);
  });
});

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { notifyRendererOfShutdown, type RendererShutdownDeps } from './renderer-shutdown';

function createLogger(): RendererShutdownDeps['logger'] {
  return { debug: vi.fn(), warn: vi.fn() };
}

describe('electron/main/renderer-shutdown', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('should resolve via ack before the timeout and clean up the listener', async () => {
    let ack: (() => void) | undefined;
    const unregister = vi.fn();
    const deps: RendererShutdownDeps = {
      send: vi.fn(() => true),
      waitForAck: vi.fn((onAck) => {
        ack = onAck;
        return unregister;
      }),
      logger: createLogger(),
    };

    const promise = notifyRendererOfShutdown(deps, 750);
    // Renderer acknowledges quickly, well before the timeout.
    ack?.();
    await expect(promise).resolves.toBeUndefined();

    expect(deps.send).toHaveBeenCalledOnce();
    expect(unregister).toHaveBeenCalledOnce();
  });

  it('should resolve via timeout when no ack arrives', async () => {
    const unregister = vi.fn();
    const deps: RendererShutdownDeps = {
      send: vi.fn(() => true),
      waitForAck: vi.fn(() => unregister),
      logger: createLogger(),
    };

    let settled = false;
    const promise = notifyRendererOfShutdown(deps, 750).then(() => {
      settled = true;
    });

    // Not yet: still within the timeout window.
    await vi.advanceTimersByTimeAsync(749);
    expect(settled).toBe(false);

    await vi.advanceTimersByTimeAsync(1);
    await promise;
    expect(settled).toBe(true);
    expect(unregister).toHaveBeenCalledOnce();
  });

  it('should resolve immediately without waiting when there is no renderer', async () => {
    const deps: RendererShutdownDeps = {
      send: vi.fn(() => false),
      waitForAck: vi.fn(),
      logger: createLogger(),
    };

    await expect(notifyRendererOfShutdown(deps, 750)).resolves.toBeUndefined();
    expect(deps.waitForAck).not.toHaveBeenCalled();
  });

  it('should resolve when send throws and never register a listener', async () => {
    const deps: RendererShutdownDeps = {
      send: vi.fn(() => {
        throw new Error('webContents destroyed');
      }),
      waitForAck: vi.fn(),
      logger: createLogger(),
    };

    await expect(notifyRendererOfShutdown(deps, 750)).resolves.toBeUndefined();
    expect(deps.waitForAck).not.toHaveBeenCalled();
    expect(deps.logger.warn).toHaveBeenCalled();
  });

  it('should resolve when registering the ack listener throws', async () => {
    const deps: RendererShutdownDeps = {
      send: vi.fn(() => true),
      waitForAck: vi.fn(() => {
        throw new Error('ipcMain gone');
      }),
      logger: createLogger(),
    };

    await expect(notifyRendererOfShutdown(deps, 750)).resolves.toBeUndefined();
    expect(deps.logger.warn).toHaveBeenCalled();
  });

  it('should ignore a late ack after the timeout has resolved', async () => {
    let ack: (() => void) | undefined;
    const unregister = vi.fn();
    const deps: RendererShutdownDeps = {
      send: vi.fn(() => true),
      waitForAck: vi.fn((onAck) => {
        ack = onAck;
        return unregister;
      }),
      logger: createLogger(),
    };

    const promise = notifyRendererOfShutdown(deps, 750);
    await vi.advanceTimersByTimeAsync(750);
    await promise;

    // A stray ack arriving after resolution must not throw or double-cleanup.
    expect(() => ack?.()).not.toThrow();
    expect(unregister).toHaveBeenCalledOnce();
  });
});

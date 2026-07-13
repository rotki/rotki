import { beforeEach, describe, expect, it, vi } from 'vitest';
import { createResourceManager } from '@/modules/wallet/bridge/resource-management';

describe('createResourceManager', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should start with an idle resource state', () => {
    const { resources } = createResourceManager();
    expect(resources.isSetupInProgress).toBe(false);
    expect(resources.setupAbortController).toBeNull();
    expect(resources.setupTimeout).toBeNull();
  });

  it('should abort an ongoing controller and reset flags on cleanup', () => {
    const { cleanupResources, resources } = createResourceManager();
    const controller = new AbortController();
    resources.setupAbortController = controller;
    resources.isSetupInProgress = true;

    cleanupResources();

    expect(controller.signal.aborted).toBe(true);
    expect(resources.setupAbortController).toBeNull();
    expect(resources.isSetupInProgress).toBe(false);
  });

  it('should not re-abort a controller that is already aborted', () => {
    const { cleanupResources, resources } = createResourceManager();
    const controller = new AbortController();
    controller.abort();
    const abortSpy = vi.spyOn(controller, 'abort');
    resources.setupAbortController = controller;

    cleanupResources();

    expect(abortSpy).not.toHaveBeenCalled();
    expect(resources.setupAbortController).toBeNull();
  });

  it('should clear a pending timeout on cleanup', () => {
    vi.useFakeTimers();
    try {
      const clearSpy = vi.spyOn(globalThis, 'clearTimeout');
      const { cleanupResources, resources } = createResourceManager();
      const timeout = setTimeout(() => {}, 1000);
      resources.setupTimeout = timeout;

      cleanupResources();

      expect(clearSpy).toHaveBeenCalledWith(timeout);
      expect(resources.setupTimeout).toBeNull();
    }
    finally {
      vi.useRealTimers();
    }
  });

  it('should be a no-op when there is nothing to clean up', () => {
    const { cleanupResources, resources } = createResourceManager();
    expect(() => cleanupResources()).not.toThrow();
    expect(resources.setupAbortController).toBeNull();
    expect(resources.setupTimeout).toBeNull();
    expect(resources.isSetupInProgress).toBe(false);
  });
});

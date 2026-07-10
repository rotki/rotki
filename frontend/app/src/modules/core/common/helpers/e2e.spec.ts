import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { attemptPolyfillResizeObserver } from '@/modules/core/common/helpers/e2e';

class FakeResizeObserver {
  static instances: FakeResizeObserver[] = [];
  callback: ResizeObserverCallback;
  observe = vi.fn();
  unobserve = vi.fn();
  disconnect = vi.fn();

  constructor(callback: ResizeObserverCallback) {
    this.callback = callback;
    FakeResizeObserver.instances.push(this);
  }

  trigger(entries: ResizeObserverEntry[]): void {
    this.callback(entries, this);
  }
}

describe('attemptPolyfillResizeObserver', () => {
  beforeEach(() => {
    FakeResizeObserver.instances = [];
    vi.stubGlobal('ResizeObserver', FakeResizeObserver);
    vi.stubGlobal('requestAnimationFrame', (cb: FrameRequestCallback): number => {
      cb(0);
      return 0;
    });
    vi.spyOn(console, 'warn').mockImplementation(() => {});
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.unstubAllEnvs();
    vi.restoreAllMocks();
  });

  it('should do nothing when VITE_E2E is not set', () => {
    vi.stubEnv('VITE_E2E', '');
    attemptPolyfillResizeObserver();
    expect(window.ResizeObserver).toBe(FakeResizeObserver);
    expect(console.warn).not.toHaveBeenCalled();
  });

  it('should install the polyfill and warn when VITE_E2E is set', () => {
    vi.stubEnv('VITE_E2E', 'true');
    attemptPolyfillResizeObserver();
    expect(window.ResizeObserver).not.toBe(FakeResizeObserver);
    expect(console.warn).toHaveBeenCalledWith(expect.stringContaining('polyfill for ResizeObserver'));
  });

  it('should forward observe, unobserve and disconnect to the real observer', () => {
    vi.stubEnv('VITE_E2E', 'true');
    attemptPolyfillResizeObserver();

    const observer = new window.ResizeObserver(vi.fn());
    const element = document.createElement('div');
    observer.observe(element);
    observer.unobserve(element);
    observer.disconnect();

    const real = FakeResizeObserver.instances[0];
    expect(real.observe).toHaveBeenCalledWith(element);
    expect(real.unobserve).toHaveBeenCalledWith(element);
    expect(real.disconnect).toHaveBeenCalled();
  });

  it('should batch resize callbacks through an animation frame', () => {
    vi.stubEnv('VITE_E2E', 'true');
    attemptPolyfillResizeObserver();

    const userCallback = vi.fn();
    const observer = new window.ResizeObserver(userCallback);
    expect(observer).toBeDefined();
    const real = FakeResizeObserver.instances[0];
    const entries: ResizeObserverEntry[] = [];

    real.trigger(entries);

    expect(userCallback).toHaveBeenCalledTimes(1);
    expect(userCallback).toHaveBeenCalledWith(entries, expect.anything());
  });

  it('should collapse repeated triggers of the same observer into one callback', () => {
    vi.stubEnv('VITE_E2E', 'true');
    let flush: FrameRequestCallback | undefined;
    vi.stubGlobal('requestAnimationFrame', (cb: FrameRequestCallback): number => {
      flush = cb;
      return 1;
    });
    attemptPolyfillResizeObserver();

    const userCallback = vi.fn();
    const observer = new window.ResizeObserver(userCallback);
    expect(observer).toBeDefined();
    const real = FakeResizeObserver.instances[0];
    const first: ResizeObserverEntry[] = [];
    const second: ResizeObserverEntry[] = [];

    real.trigger(first);
    real.trigger(second);
    flush?.(0);

    expect(userCallback).toHaveBeenCalledTimes(1);
    expect(userCallback).toHaveBeenLastCalledWith(second, expect.anything());
  });
});

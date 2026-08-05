import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { combineAbortSignals } from './abort-signals';

describe('combineAbortSignals', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('should return the shared signal untouched when there is nothing to combine', () => {
    const shared = new AbortController().signal;

    expect(combineAbortSignals(shared).signal).toBe(shared);
    expect(combineAbortSignals(shared, null).signal).toBe(shared);
    expect(combineAbortSignals(shared, null, 0).signal).toBe(shared);
  });

  it('should abort when the shared signal aborts', () => {
    const shared = new AbortController();
    const request = new AbortController();

    const { signal } = combineAbortSignals(shared.signal, request.signal);
    expect(signal.aborted).toBe(false);

    shared.abort();
    expect(signal.aborted).toBe(true);
  });

  it('should abort when the request signal aborts', () => {
    const shared = new AbortController();
    const request = new AbortController();

    const { signal } = combineAbortSignals(shared.signal, request.signal);
    expect(signal.aborted).toBe(false);

    request.abort();
    expect(signal.aborted).toBe(true);
  });

  it('should start aborted when either signal already is', () => {
    const shared = new AbortController();
    const request = new AbortController();
    request.abort();

    expect(combineAbortSignals(shared.signal, request.signal).signal.aborted).toBe(true);
  });

  it('should abort once the timeout elapses', () => {
    const { signal } = combineAbortSignals(new AbortController().signal, undefined, 10_000);

    vi.advanceTimersByTime(9999);
    expect(signal.aborted).toBe(false);

    vi.advanceTimersByTime(1);
    expect(signal.aborted).toBe(true);
    expect(signal.reason).toBeInstanceOf(DOMException);
    expect(signal.reason.name).toBe('TimeoutError');
  });

  it('should not abort after dispose', () => {
    const { dispose, signal } = combineAbortSignals(new AbortController().signal, undefined, 10_000);

    dispose();
    vi.advanceTimersByTime(60_000);

    expect(signal.aborted).toBe(false);
  });

  it('should leave no timer pending once disposed', () => {
    const { dispose } = combineAbortSignals(new AbortController().signal, undefined, 600_000);
    expect(vi.getTimerCount()).toBe(1);

    dispose();
    expect(vi.getTimerCount()).toBe(0);
  });
});

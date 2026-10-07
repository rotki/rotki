import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { backoff, generateUUID } from './utils';

describe('backoff', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('should retry a failure after the delay, doubling it each time', async () => {
    const call = vi.fn<() => Promise<string>>()
      .mockRejectedValueOnce(new Error('first'))
      .mockRejectedValueOnce(new Error('second'))
      .mockResolvedValue('ok');

    const result = backoff(3, call, 1000);
    await vi.advanceTimersByTimeAsync(1000);
    expect(call).toHaveBeenCalledTimes(2);
    await vi.advanceTimersByTimeAsync(2000);

    await expect(result).resolves.toBe('ok');
    expect(call).toHaveBeenCalledTimes(3);
  });

  it('should throw the last failure once the retries run out', async () => {
    const call = vi.fn<() => Promise<string>>().mockRejectedValue(new Error('down'));

    const result = expect(backoff(2, call, 1000)).rejects.toThrow('down');
    await vi.advanceTimersByTimeAsync(1000);

    await result;
    expect(call).toHaveBeenCalledTimes(2);
  });

  it('should stop retrying as soon as the signal aborts during a wait', async () => {
    const controller = new AbortController();
    const call = vi.fn<() => Promise<string>>().mockRejectedValue(new Error('refused'));

    const result = expect(backoff(3, call, 10_000, controller.signal)).rejects.toThrow('refused');
    await vi.advanceTimersByTimeAsync(100);
    controller.abort();

    await result;
    expect(call).toHaveBeenCalledOnce();
    expect(vi.getTimerCount()).toBe(0);
  });

  it('should not retry when the signal has already aborted', async () => {
    const controller = new AbortController();
    controller.abort();
    const call = vi.fn<() => Promise<string>>().mockRejectedValue(new Error('refused'));

    await expect(backoff(3, call, 10_000, controller.signal)).rejects.toThrow('refused');

    expect(call).toHaveBeenCalledOnce();
  });
});

describe('generateUUID', () => {
  const UUID_V4_REGEX = /^[\da-f]{8}-[\da-f]{4}-4[\da-f]{3}-[89ab][\da-f]{3}-[\da-f]{12}$/i;

  it('should return a valid UUID v4 format', () => {
    const uuid = generateUUID();
    expect(uuid).toMatch(UUID_V4_REGEX);
  });

  it('should generate unique UUIDs', () => {
    const uuids = new Set<string>();
    for (let i = 0; i < 100; i++) {
      uuids.add(generateUUID());
    }
    expect(uuids.size).toBe(100);
  });

  it('should have correct version (4) in the third group', () => {
    const uuid = generateUUID();
    const parts = uuid.split('-');
    expect(parts[2][0]).toBe('4');
  });

  it('should have correct variant (8, 9, a, or b) in the fourth group', () => {
    const uuid = generateUUID();
    const parts = uuid.split('-');
    expect(['8', '9', 'a', 'b']).toContain(parts[3][0].toLowerCase());
  });

  describe('fallback behavior', () => {
    afterEach(() => {
      vi.unstubAllGlobals();
    });

    it('should fall back to getRandomValues when randomUUID is undefined', () => {
      const mockGetRandomValues = vi.fn((array: Uint8Array) => {
        for (let i = 0; i < array.length; i++) {
          array[i] = Math.floor(Math.random() * 256);
        }
        return array;
      });

      vi.stubGlobal('crypto', {
        getRandomValues: mockGetRandomValues,
        randomUUID: undefined,
      });

      const uuid = generateUUID();
      expect(uuid).toMatch(UUID_V4_REGEX);
      expect(mockGetRandomValues).toHaveBeenCalled();
    });

    it('should fall back to Math.random when crypto.getRandomValues is undefined', () => {
      vi.stubGlobal('crypto', {
        getRandomValues: undefined,
        randomUUID: undefined,
      });

      const uuid = generateUUID();
      expect(uuid).toMatch(UUID_V4_REGEX);
    });

    it('should fall back to Math.random when crypto is undefined', () => {
      vi.stubGlobal('crypto', undefined);

      const uuid = generateUUID();
      expect(uuid).toMatch(UUID_V4_REGEX);
    });
  });
});

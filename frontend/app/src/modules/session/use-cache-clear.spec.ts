import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { useCacheClear } from './use-cache-clear';

type Source = 'a' | 'b';

const clearable: { id: Source; text: string }[] = [
  { id: 'a', text: 'Cache A' },
  { id: 'b', text: 'Cache B' },
];

const message = {
  error: (source: string, reason: string): string => `failed ${source}: ${reason}`,
  success: (source: string): string => `cleared ${source}`,
};

describe('useCacheClear', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('should clear straight away', async () => {
    const clearHandle = vi.fn().mockResolvedValue(undefined);
    const { pending, request, status } = useCacheClear<Source>(clearable, clearHandle, message);
    await request('b');
    expect(clearHandle).toHaveBeenCalledWith('b');
    expect(get(status)).toEqual({ error: '', success: 'cleared Cache B' });
    expect(get(pending)).toBe(false);
  });

  it('should set a success status after clearing', async () => {
    const clearHandle = vi.fn().mockResolvedValue(undefined);
    const { pending, request, status } = useCacheClear<Source>(clearable, clearHandle, message);
    await request('a');
    expect(clearHandle).toHaveBeenCalledWith('a');
    expect(get(status)).toEqual({ error: '', success: 'cleared Cache A' });
    expect(get(pending)).toBe(false);
  });

  it('should clear the success status after five seconds', async () => {
    const clearHandle = vi.fn().mockResolvedValue(undefined);
    const { request, status } = useCacheClear<Source>(clearable, clearHandle, message);
    await request('a');
    expect(get(status)).not.toBeNull();
    await vi.advanceTimersByTimeAsync(5000);
    expect(get(status)).toBeNull();
  });

  it('should set no status when the handle resolves false, as for a cancelled run', async () => {
    const clearHandle = vi.fn().mockResolvedValue(false);
    const { pending, request, status } = useCacheClear<Source>(clearable, clearHandle, message);
    await request('a');
    expect(clearHandle).toHaveBeenCalledWith('a');
    expect(get(status)).toBeNull();
    expect(get(pending)).toBe(false);
  });

  it('should set an error status carrying the rejection message when the handle rejects', async () => {
    const clearHandle = vi.fn().mockRejectedValue(new Error('boom'));
    const { pending, request, status } = useCacheClear<Source>(clearable, clearHandle, message);
    await request('b');
    expect(get(status)).toEqual({ error: 'failed Cache B: boom', success: '' });
    expect(get(pending)).toBe(false);
  });

  it('should keep the error status instead of clearing it after five seconds', async () => {
    const clearHandle = vi.fn().mockRejectedValue(new Error('boom'));
    const { request, status } = useCacheClear<Source>(clearable, clearHandle, message);
    await request('b');
    await vi.advanceTimersByTimeAsync(5000);
    expect(get(status)).toEqual({ error: 'failed Cache B: boom', success: '' });
  });
});

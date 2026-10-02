import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { useCacheClear } from './use-cache-clear';

const show = vi.fn();

vi.mock('@/modules/core/common/use-confirm-store', () => ({
  useConfirmStore: (): { show: typeof show } => ({ show }),
}));

type Source = 'a' | 'b';

const clearable: { id: Source; text: string }[] = [
  { id: 'a', text: 'Cache A' },
  { id: 'b', text: 'Cache B' },
];

const message = {
  error: (source: string, reason: string): string => `failed ${source}: ${reason}`,
  success: (source: string): string => `cleared ${source}`,
};

function confirmText(text: string): { title: string; message: string } {
  return {
    title: `Clear ${text}?`,
    message: `Really clear ${text}?`,
  };
}

describe('useCacheClear', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('should open the confirmation dialog with resolved text', () => {
    const clearHandle = vi.fn().mockResolvedValue(undefined);
    const { showConfirmation } = useCacheClear<Source>(clearable, clearHandle, message, confirmText);
    showConfirmation('a');
    expect(show).toHaveBeenCalledWith(
      { title: 'Clear Cache A?', message: 'Really clear Cache A?' },
      expect.any(Function),
    );
  });

  it('should set a success status after clearing', async () => {
    const clearHandle = vi.fn().mockResolvedValue(undefined);
    const { pending, showConfirmation, status } = useCacheClear<Source>(clearable, clearHandle, message, confirmText);
    showConfirmation('a');
    await show.mock.calls[0][1]();
    expect(clearHandle).toHaveBeenCalledWith('a');
    expect(get(status)).toEqual({ error: '', success: 'cleared Cache A' });
    expect(get(pending)).toBe(false);
  });

  it('should clear the success status after five seconds', async () => {
    const clearHandle = vi.fn().mockResolvedValue(undefined);
    const { showConfirmation, status } = useCacheClear<Source>(clearable, clearHandle, message, confirmText);
    showConfirmation('a');
    await show.mock.calls[0][1]();
    expect(get(status)).not.toBeNull();
    await vi.advanceTimersByTimeAsync(5000);
    expect(get(status)).toBeNull();
  });

  it('should set an error status carrying the rejection message when the handle rejects', async () => {
    const clearHandle = vi.fn().mockRejectedValue(new Error('boom'));
    const { pending, showConfirmation, status } = useCacheClear<Source>(clearable, clearHandle, message, confirmText);
    showConfirmation('b');
    await show.mock.calls[0][1]();
    expect(get(status)).toEqual({ error: 'failed Cache B: boom', success: '' });
    expect(get(pending)).toBe(false);
  });

  it('should keep the error status instead of clearing it after five seconds', async () => {
    const clearHandle = vi.fn().mockRejectedValue(new Error('boom'));
    const { showConfirmation, status } = useCacheClear<Source>(clearable, clearHandle, message, confirmText);
    showConfirmation('b');
    await show.mock.calls[0][1]();
    await vi.advanceTimersByTimeAsync(5000);
    expect(get(status)).toEqual({ error: 'failed Cache B: boom', success: '' });
  });
});

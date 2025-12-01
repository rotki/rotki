import { wait } from '@shared/utils';
import { FetchError } from 'ofetch';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { withRetry } from './with-retry';

vi.mock('@shared/utils', () => ({
  wait: vi.fn(async () => Promise.resolve()),
}));

function createTimeoutError(): FetchError {
  const error = new FetchError('timeout of 30000ms exceeded');
  return error;
}

function createAbortError(): DOMException {
  return new DOMException('The operation was aborted', 'AbortError');
}

describe('withRetry', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should resolve if the request succeeds on the first attempt', async () => {
    const requestFn = vi.fn().mockResolvedValue('success');
    const result = await withRetry(requestFn);
    expect(result).toBe('success');
    expect(requestFn).toHaveBeenCalledTimes(1);
  });

  it('should retry and resolve if the request succeeds after retries (FetchError timeout)', async () => {
    const requestFn = vi
      .fn()
      .mockRejectedValueOnce(createTimeoutError())
      .mockResolvedValue('success');

    const result = await withRetry(requestFn, { maxRetries: 2, retryDelay: 1000 });
    expect(result).toBe('success');
    expect(requestFn).toHaveBeenCalledTimes(2);
    expect(wait).toHaveBeenCalledWith(1000);
  });

  it('should retry and resolve if the request succeeds after retries (AbortError)', async () => {
    const requestFn = vi
      .fn()
      .mockRejectedValueOnce(createAbortError())
      .mockResolvedValue('success');

    const result = await withRetry(requestFn, { maxRetries: 2, retryDelay: 1000 });
    expect(result).toBe('success');
    expect(requestFn).toHaveBeenCalledTimes(2);
    expect(wait).toHaveBeenCalledWith(1000);
  });

  it('should throw an error if retries exceed maxRetries', async () => {
    const requestFn = vi.fn().mockRejectedValue(createTimeoutError());

    await expect(
      withRetry(requestFn, { maxRetries: 2, retryDelay: 1000 }),
    ).rejects.toThrow('timeout of 30000ms exceeded');
    expect(requestFn).toHaveBeenCalledTimes(3);
    expect(wait).toHaveBeenCalledTimes(2);
    expect(wait).toHaveBeenLastCalledWith(2000);
  });

  it('should throw immediately for non-timeout errors', async () => {
    const requestFn = vi.fn().mockRejectedValue(new Error('OtherError'));

    await expect(withRetry(requestFn)).rejects.toThrow('OtherError');
    expect(requestFn).toHaveBeenCalledTimes(1);
    expect(wait).not.toHaveBeenCalled();
  });
});

import type { ConsolaInstance } from 'consola';
import { FetchError } from 'ofetch';
import { describe, expect, it, vi } from 'vitest';
import { RequestCancelledError } from '@/modules/core/api/request-queue/errors';
import { demoteCancellations } from './demote-cancellations';

type LogFn = ConsolaInstance['error'];

function createLogFn(): LogFn {
  return Object.assign(vi.fn<(...args: unknown[]) => void>(), { raw: vi.fn<(...args: unknown[]) => void>() });
}

describe('demoteCancellations', () => {
  it('should log a cancelled request through the fallback', () => {
    const error = createLogFn();
    const debug = createLogFn();

    demoteCancellations(error, debug)('Failed to fetch tags:', new RequestCancelledError('No live session'));

    expect(error).not.toHaveBeenCalled();
    expect(debug).toHaveBeenCalledWith('Failed to fetch tags:', expect.any(RequestCancelledError));
  });

  it('should log an aborted fetch through the fallback', () => {
    const error = createLogFn();
    const debug = createLogFn();
    const aborted = new FetchError('aborted');
    aborted.cause = new DOMException('The operation was aborted.', 'AbortError');

    demoteCancellations(error, debug)(aborted);

    expect(error).not.toHaveBeenCalled();
    expect(debug).toHaveBeenCalledOnce();
  });

  it('should log a real failure at its own level', () => {
    const error = createLogFn();
    const debug = createLogFn();

    demoteCancellations(error, debug)('Failed to fetch tags:', new Error('backend down'));

    expect(error).toHaveBeenCalledWith('Failed to fetch tags:', expect.any(Error));
    expect(debug).not.toHaveBeenCalled();
  });

  it('should not wrap a function it already wrapped, so a reloaded logger does not stack wrappers', () => {
    const debug = createLogFn();
    const once = demoteCancellations(createLogFn(), debug);

    expect(demoteCancellations(once, debug)).toBe(once);
  });

  it('should keep the raw variant of the wrapped function', () => {
    const error = createLogFn();

    expect(demoteCancellations(error, createLogFn()).raw).toBe(error.raw);
  });
});

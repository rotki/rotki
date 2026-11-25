import { bigNumberify, type HistoricalAssetPriceResponse } from '@rotki/common';
import { FetchError } from 'ofetch';
import { err, ok } from 'plainfp/result';
import { describe, expect, it } from 'vitest';
import { ZodError } from 'zod';
import { ApiRequestError } from '@/modules/core/api/types/errors';
import { BackendCancelled, Cancelled, type TaskError, TaskFailed } from '@/modules/core/tasks/task-result';
import { classifyOutcome } from '@/modules/statistics/pricing/backfill-outcome';

function response(rateLimitedPricesTimestamps: number[] = [], failedPricesTimestamps: number[] = []): HistoricalAssetPriceResponse {
  return { failedPricesTimestamps, noPricesTimestamps: [], prices: { 86400: bigNumberify('0.9') }, rateLimitedPricesTimestamps };
}

describe('modules/statistics/pricing/backfill-outcome', () => {
  describe('classifyOutcome', () => {
    it('should call a priced response ok, and rate limited when an oracle throttled any day', () => {
      expect(classifyOutcome(ok(response()))).toBe('ok');
      expect(classifyOutcome(ok(response([86400])))).toBe('rate-limited');
    });

    it('should call a response unreachable when an oracle could not be reached for a day, unless one also throttled', () => {
      expect(classifyOutcome(ok(response([], [172800])))).toBe('unreachable');
      expect(classifyOutcome(ok(response([86400], [172800])))).toBe('rate-limited');
    });

    it('should tell a cancellation from a failure', () => {
      expect(classifyOutcome(err(Cancelled({ message: 'stopped' })))).toBe('cancelled');
      expect(classifyOutcome(err(BackendCancelled({ message: 'stopped' })))).toBe('cancelled');
      expect(classifyOutcome(err(TaskFailed({ message: 'the backend rejected the request' })))).toBe('failed');
    });

    it('should read the cause of a failed task from the error the task layer wraps, as it does for a 502', () => {
      const failed = (failureCause: 'network' | 'rate_limited' | 'auth'): TaskError => TaskFailed({
        cause: new ApiRequestError('failed', { failureCause, status: 502 }),
        message: 'failed',
      });
      expect(classifyOutcome(err(failed('network')))).toBe('unreachable');
      expect(classifyOutcome(err(failed('rate_limited')))).toBe('rate-limited');
      expect(classifyOutcome(err(failed('auth')))).toBe('failed');
    });

    it('should call a request that got no response at all unreachable, as no backend named a cause', () => {
      const noResponse = new FetchError('[POST] "http://127.0.0.1:4242/api/1/balances/historical/asset/prices": <no response> fetch failed');
      expect(classifyOutcome(err(TaskFailed({ cause: noResponse, message: 'fetch failed' })))).toBe('unreachable');
    });

    it('should call a response that does not match the schema invalid, not a failure of the oracles', () => {
      expect(classifyOutcome(err(TaskFailed({ cause: new ZodError([]), message: 'bad response' })))).toBe('invalid');
    });
  });
});

import { bigNumberify, type HistoricalAssetPriceResponse } from '@rotki/common';
import { err, ok } from 'plainfp/result';
import { describe, expect, it } from 'vitest';
import { ZodError } from 'zod';
import { BackendCancelled, Cancelled, TaskFailed } from '@/modules/core/tasks/task-result';
import { classifyOutcome } from '@/modules/statistics/pricing/use-backfill-requests';

function response(rateLimitedPricesTimestamps: number[] = []): HistoricalAssetPriceResponse {
  return { noPricesTimestamps: [], prices: { 86400: bigNumberify('0.9') }, rateLimitedPricesTimestamps };
}

describe('modules/statistics/pricing/use-backfill-requests', () => {
  describe('classifyOutcome', () => {
    it('should call a priced response ok, and rate limited when an oracle throttled any day', () => {
      expect(classifyOutcome(ok(response()))).toBe('ok');
      expect(classifyOutcome(ok(response([86400])))).toBe('rate-limited');
    });

    it('should tell a cancellation from a failure', () => {
      expect(classifyOutcome(err(Cancelled({ message: 'stopped' })))).toBe('cancelled');
      expect(classifyOutcome(err(BackendCancelled({ message: 'stopped' })))).toBe('cancelled');
      expect(classifyOutcome(err(TaskFailed({ message: 'the backend rejected the request' })))).toBe('failed');
    });

    it('should call a response that does not match the schema invalid, not a failure of the oracles', () => {
      expect(classifyOutcome(err(TaskFailed({ cause: new ZodError([]), message: 'bad response' })))).toBe('invalid');
    });
  });
});

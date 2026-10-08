import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { createOraclePenalizedHandler } from '@/modules/core/messaging/handlers/oracle-penalized';
import { RaisedConditionKind, useRaisedConditionsStore } from '@/modules/shell/action-center/use-raised-conditions-store';

const NOW = new Date('2026-10-08T12:00:00Z').getTime();
const PENALTY_SECONDS = 1800;
const PENALTY_MS = PENALTY_SECONDS * 1000;

describe('createOraclePenalizedHandler', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.useFakeTimers();
    vi.setSystemTime(NOW);
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('should raise the oracle\'s row until its penalty ends, and create no notification', async () => {
    const result = await createOraclePenalizedHandler().handle({ oracle: 'coingecko', penaltyDuration: PENALTY_SECONDS, reason: 'timeout' });

    expect(result).toBeUndefined();
    expect(useRaisedConditionsStore().conditions).toEqual([
      { kind: RaisedConditionKind.ORACLE_PENALIZED, oracle: 'coingecko', reason: 'timeout', until: NOW + PENALTY_MS },
    ]);
  });

  it('should keep one row per oracle', async () => {
    const handler = createOraclePenalizedHandler();

    await handler.handle({ oracle: 'coingecko', penaltyDuration: PENALTY_SECONDS, reason: 'timeout' });
    await handler.handle({ oracle: 'defillama', penaltyDuration: PENALTY_SECONDS, reason: 'errors' });
    await handler.handle({ oracle: 'coingecko', penaltyDuration: PENALTY_SECONDS, reason: 'errors' });

    expect(useRaisedConditionsStore().conditions.map(condition => 'oracle' in condition && condition.oracle)).toEqual(['coingecko', 'defillama']);
  });

  it('should take the row down once the penalty ends', async () => {
    await createOraclePenalizedHandler().handle({ oracle: 'coingecko', penaltyDuration: PENALTY_SECONDS, reason: 'timeout' });

    vi.advanceTimersByTime(PENALTY_MS - 1);
    expect(useRaisedConditionsStore().conditions).toHaveLength(1);

    vi.advanceTimersByTime(1);
    expect(useRaisedConditionsStore().conditions).toEqual([]);
  });

  it('should keep the row of a penalty renewed before the first one ended', async () => {
    const handler = createOraclePenalizedHandler();
    await handler.handle({ oracle: 'coingecko', penaltyDuration: PENALTY_SECONDS, reason: 'timeout' });

    vi.advanceTimersByTime(PENALTY_MS / 2);
    await handler.handle({ oracle: 'coingecko', penaltyDuration: PENALTY_SECONDS, reason: 'timeout' });
    vi.advanceTimersByTime(PENALTY_MS / 2);

    expect(useRaisedConditionsStore().conditions).toHaveLength(1);
  });

  it('should date a held penalty from when it was sent, and raise nothing once it has run out', async () => {
    const handler = createOraclePenalizedHandler();

    await handler.handle({ oracle: 'coingecko', penaltyDuration: PENALTY_SECONDS, reason: 'timeout' }, { count: 1, lastSent: new Date(NOW - PENALTY_MS - 1) });
    await handler.handle({ oracle: 'defillama', penaltyDuration: PENALTY_SECONDS, reason: 'timeout' }, { count: 1, lastSent: new Date(NOW - 1000) });

    expect(useRaisedConditionsStore().conditions).toEqual([
      { kind: RaisedConditionKind.ORACLE_PENALIZED, oracle: 'defillama', reason: 'timeout', until: NOW - 1000 + PENALTY_MS },
    ]);
  });
});

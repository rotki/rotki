import { describe, expect, it } from 'vitest';
import { FailureCause } from '@/modules/core/api/failure-cause';
import { fixRouteOf } from '@/modules/task-center/activity-fix-route';
import { ActivityKind } from '@/modules/task-center/core/types';

describe('fixRouteOf', () => {
  it.each([
    [ActivityKind.EXCHANGE_BALANCES, '/accounts/exchanges/'],
    [ActivityKind.BANK_BALANCES, '/accounts/banks/'],
    [ActivityKind.SYNC, '/api-keys/premium/'],
    [ActivityKind.TX_SYNC, '/api-keys/external/'],
  ])('should send a rejected key on %s to where that key is edited', (kind, route) => {
    expect(fixRouteOf({ failureCause: FailureCause.AUTH, kind })).toEqual({ name: route });
  });

  it('should offer nothing for a failure a new key would not fix', () => {
    expect(fixRouteOf({ failureCause: FailureCause.NETWORK, kind: ActivityKind.EXCHANGE_BALANCES })).toBeUndefined();
    expect(fixRouteOf({ failureCause: undefined, kind: ActivityKind.EXCHANGE_BALANCES })).toBeUndefined();
  });

  it('should offer nothing for work whose keys live in more than one place', () => {
    expect(fixRouteOf({ failureCause: FailureCause.AUTH, kind: ActivityKind.BLOCKCHAIN_BALANCES })).toBeUndefined();
  });
});

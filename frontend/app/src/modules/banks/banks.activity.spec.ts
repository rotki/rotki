import { describe, expect, it } from 'vitest';
import { bankBalancesActivity } from '@/modules/banks/banks.activity';
import { EXCHANGE_LANE } from '@/modules/task-center/core/orchestrator/spec';

describe('bank activity ids', () => {
  it('should give the bank balances the bare kind, on the exchange lane', () => {
    expect(bankBalancesActivity.id()).toBe('bank-balances');
    expect(bankBalancesActivity.laneOf?.()).toBe(EXCHANGE_LANE);
  });
});

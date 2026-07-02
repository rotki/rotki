import type { AccountingRuleEntry } from '@/modules/settings/types/accounting';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useRuleEventsLink } from '@/modules/settings/accounting/rule/use-rule-events-link';

const push = vi.fn(async (): Promise<void> => {});

vi.mock('vue-router', () => ({
  useRouter: (): { push: typeof push } => ({ push }),
}));

function buildRule(overrides: Partial<AccountingRuleEntry> = {}): AccountingRuleEntry {
  return {
    accountingTreatment: null,
    countCostBasisPnl: { value: false },
    countEntireAmountSpend: { value: false },
    counterparty: null,
    eventSubtype: 'reward',
    eventType: 'staking',
    identifier: 1,
    taxable: { value: false },
    ...overrides,
  };
}

describe('useRuleEventsLink', () => {
  beforeEach(() => {
    push.mockClear();
  });

  it('should navigate to the filtered history events page', () => {
    const { viewEvents } = useRuleEventsLink();
    viewEvents(buildRule({ counterparty: 'aave-v3' }));

    expect(push).toHaveBeenCalledWith({
      path: '/history/events',
      query: { counterparties: 'aave-v3', eventSubtypes: 'reward', eventTypes: 'staking' },
    });
  });

  it('should omit the counterparty filter when the rule has none', () => {
    const { viewEvents } = useRuleEventsLink();
    viewEvents(buildRule());

    expect(push).toHaveBeenCalledWith({
      path: '/history/events',
      query: { eventSubtypes: 'reward', eventTypes: 'staking' },
    });
  });
});

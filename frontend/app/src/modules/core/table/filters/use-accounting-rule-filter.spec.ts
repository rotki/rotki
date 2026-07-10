import type { Ref } from 'vue';
import { assert, describe, expect, it, vi } from 'vitest';
import { useAccountingRuleFilter } from '@/modules/core/table/filters/use-accounting-rule-filter';

const mockEventTypes = ref<string[]>(['spend', 'receive']);
const mockEventSubTypes = ref<string[]>(['fee', 'reward']);
const mockCounterparties = ref<string[]>(['uniswap', 'aave']);

vi.mock('vue-i18n', async importOriginal => ({
  ...await importOriginal<typeof import('vue-i18n')>(),
  useI18n: (): { t: (key: string) => string } => ({ t: (key: string): string => key }),
}));

vi.mock('@/modules/history/events/mapping/use-history-event-mappings', () => ({
  useHistoryEventMappings: (): { historyEventSubTypes: Ref<string[]>; historyEventTypes: Ref<string[]> } => ({
    historyEventSubTypes: mockEventSubTypes,
    historyEventTypes: mockEventTypes,
  }),
}));

vi.mock('@/modules/history/events/mapping/use-history-event-counterparty-mappings', () => ({
  useHistoryEventCounterpartyMappings: (): { counterparties: Ref<string[]> } => ({
    counterparties: mockCounterparties,
  }),
}));

describe('useAccountingRuleFilter', () => {
  it('should start with an empty filter', () => {
    const { filters } = useAccountingRuleFilter();
    expect(get(filters)).toEqual({});
  });

  it('should expose matchers for event type, subtype and counterparty', () => {
    const { matchers } = useAccountingRuleFilter();
    const keys = get(matchers).map(matcher => matcher.key);
    expect(keys).toEqual(['event_type', 'event_subtype', 'counterparty']);
  });

  it('should source suggestions from the history event mappings', () => {
    const { matchers } = useAccountingRuleFilter();

    const typeMatcher = get(matchers).find(matcher => matcher.key === 'event_type');
    const subtypeMatcher = get(matchers).find(matcher => matcher.key === 'event_subtype');
    const counterpartyMatcher = get(matchers).find(matcher => matcher.key === 'counterparty');
    assert(typeMatcher && 'string' in typeMatcher);
    assert(subtypeMatcher && 'string' in subtypeMatcher);
    assert(counterpartyMatcher && 'string' in counterpartyMatcher);

    expect(typeMatcher.suggestions()).toEqual(['spend', 'receive']);
    expect(subtypeMatcher.suggestions()).toEqual(['fee', 'reward']);
    expect(counterpartyMatcher.suggestions()).toEqual(['uniswap', 'aave']);
  });

  it('should validate all values as non-empty strings', () => {
    const { matchers } = useAccountingRuleFilter();
    const typeMatcher = get(matchers).find(matcher => matcher.key === 'event_type');
    assert(typeMatcher && 'string' in typeMatcher);
    expect(typeMatcher.validate('spend')).toBe(true);
    expect(typeMatcher.validate('')).toBe(false);
  });

  it('should coerce single route values into arrays', () => {
    const { RouteFilterSchema } = useAccountingRuleFilter();
    assert(RouteFilterSchema);
    expect(RouteFilterSchema.parse({ counterparties: 'uniswap', eventTypes: 'spend' }))
      .toEqual({ counterparties: ['uniswap'], eventTypes: ['spend'] });
  });

  it('should allow an empty route filter', () => {
    const { RouteFilterSchema } = useAccountingRuleFilter();
    assert(RouteFilterSchema);
    expect(RouteFilterSchema.parse({})).toEqual({});
  });
});

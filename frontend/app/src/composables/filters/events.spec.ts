import { createPinia, setActivePinia } from 'pinia';
import { afterEach, assert, beforeEach, describe, expect, it, vi } from 'vitest';
import { nextTick, type Ref } from 'vue';
import { useHistoryEventFilter } from './events';

const globalMappingData = ref<Record<string, Record<string, { default: string; exchange?: string }>>>({});

vi.mock('@/composables/history/events/mapping', () => ({
  useHistoryEventMappings: (): {
    historyEventTypeGlobalMapping: Ref<Record<string, Record<string, { default: string; exchange?: string }>>>;
    historyEventTypes: Ref<string[]>;
  } => ({
    historyEventTypeGlobalMapping: globalMappingData,
    historyEventTypes: computed<string[]>(() => Object.keys(get(globalMappingData))),
  }),
}));

vi.mock('@/composables/history/events/mapping/counterparty', () => ({
  useHistoryEventCounterpartyMappings: (): { counterparties: Ref<string[]> } => ({
    counterparties: ref<string[]>([]),
  }),
}));

vi.mock('@/composables/assets/retrieval', () => ({
  useAssetInfoRetrieval: (): { assetInfo: Ref<undefined>; assetSearch: Ref<() => never[]> } => ({
    assetInfo: ref<undefined>(undefined),
    assetSearch: ref<() => never[]>(() => []),
  }),
}));

vi.mock('@/store/history', () => ({
  useHistoryStore: (): { associatedLocations: Ref<string[]> } => ({
    associatedLocations: ref<string[]>([]),
  }),
}));

vi.mock('@/store/settings/frontend', () => ({
  useFrontendSettingsStore: (): Record<string, unknown> => ({
    dateInputFormat: ref<string>(''),
    $id: 'frontend-settings',
  }),
}));

function getMockGlobalMapping(): Record<string, Record<string, { default: string }>> {
  return {
    receive: {
      none: { default: 'receive' },
      reward: { default: 'claim_reward' },
      airdrop: { default: 'airdrop' },
    },
    spend: {
      none: { default: 'send' },
      fee: { default: 'fee' },
    },
    trade: {
      spend: { default: 'swap_out' },
      receive: { default: 'swap_in' },
      fee: { default: 'fee' },
    },
  };
}

describe('composables/filters/events', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    set(globalMappingData, {});
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe('useHistoryEventFilter', () => {
    it('does not strip event subtypes when mapping is not yet loaded', async () => {
      set(globalMappingData, {});

      const { filters } = useHistoryEventFilter({});

      set(filters, { eventTypes: ['receive'], eventSubtypes: ['none'] });
      await nextTick();

      expect(get(filters).eventSubtypes).toEqual(['none']);
    });

    it('preserves valid event subtypes once mapping loads', async () => {
      set(globalMappingData, {});

      const { filters } = useHistoryEventFilter({});

      set(filters, { eventTypes: ['receive'], eventSubtypes: ['none'] });
      await nextTick();

      set(globalMappingData, getMockGlobalMapping());
      await nextTick();

      expect(get(filters).eventSubtypes).toEqual(['none']);
    });

    it('strips invalid event subtypes once mapping loads', async () => {
      set(globalMappingData, {});

      const { filters } = useHistoryEventFilter({});

      set(filters, { eventTypes: ['receive'], eventSubtypes: ['invalid_subtype'] });
      await nextTick();

      set(globalMappingData, getMockGlobalMapping());
      await nextTick();

      expect(get(filters).eventSubtypes).toBeUndefined();
    });

    it('keeps valid subtypes and strips invalid ones from a mixed set', async () => {
      set(globalMappingData, getMockGlobalMapping());

      const { filters } = useHistoryEventFilter({});

      set(filters, { eventTypes: ['receive'], eventSubtypes: ['none', 'invalid_subtype'] });
      await nextTick();

      expect(get(filters).eventSubtypes).toEqual(['none']);
    });

    it('strips subtypes not valid for the selected event type', async () => {
      set(globalMappingData, getMockGlobalMapping());

      const { filters } = useHistoryEventFilter({});

      // 'spend' is a valid subtype of 'trade' but not of 'receive'
      set(filters, { eventTypes: ['receive'], eventSubtypes: ['spend'] });
      await nextTick();

      expect(get(filters).eventSubtypes).toBeUndefined();
    });

    it('provides event_subtype matcher with correct suggestions', async () => {
      set(globalMappingData, getMockGlobalMapping());

      const { filters, matchers } = useHistoryEventFilter({ period: true });

      set(filters, { eventTypes: ['receive'] });
      await nextTick();

      const subtypeMatcher = get(matchers).find(m => m.key === 'event_subtype');
      expect(subtypeMatcher).toBeDefined();
      assert('string' in subtypeMatcher!);

      const suggestions = subtypeMatcher.suggestions();
      expect(suggestions).toContain('none');
      expect(suggestions).toContain('reward');
      expect(suggestions).toContain('airdrop');
      expect(suggestions).not.toContain('fee');
    });
  });
});

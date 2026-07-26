import { HistoryEventEntryType } from '@rotki/common';
import { get } from '@vueuse/core';
import flushPromises from 'flush-promises';
import { createPinia, setActivePinia } from 'pinia';
import { assert, beforeAll, beforeEach, describe, expect, it, vi } from 'vitest';
import { ref } from 'vue';
import { convertToTimestamp, setupDayjs } from '@/modules/core/common/data/date';
import { assetSuggestions } from '@/modules/core/common/display/assets';
import { useMainStore } from '@/modules/core/common/use-main-store';
import { useSupportedChains } from '@/modules/core/common/use-supported-chains';
import { useHistoryEventFilter } from '@/modules/core/table/filters/use-events-filter';

vi.mock('@/modules/core/common/display/assets', async () => {
  const mod = await vi.importActual<typeof import('@/modules/core/common/display/assets')>(
    '@/modules/core/common/display/assets',
  );
  return {
    ...mod,
    assetSuggestions: vi.fn().mockReturnValue([]),
  };
});

const mockCounterpartyMappings = vi.hoisted(() => ({
  useHistoryEventCounterpartyMappings: vi.fn(),
}));

const mockEventMappings = vi.hoisted(() => ({
  useHistoryEventMappings: vi.fn(),
}));

vi.mock('@/modules/history/events/mapping/use-history-event-counterparty-mappings', () => mockCounterpartyMappings);
vi.mock('@/modules/history/events/mapping/use-history-event-mappings', () => mockEventMappings);

describe('useHistoryEventFilter', () => {
  beforeAll(async () => {
    setupDayjs();
    setActivePinia(createPinia());

    mockCounterpartyMappings.useHistoryEventCounterpartyMappings.mockReturnValue({
      counterparties: ref([]),
      fetchCounterparties: vi.fn(),
      getBaseCounterpartyData: vi.fn(),
      getCounterpartyData: vi.fn().mockReturnValue(computed(() => ({}))),
      getEventCounterpartyData: vi.fn().mockReturnValue(computed(() => undefined)),
    });

    mockEventMappings.useHistoryEventMappings.mockReturnValue({
      eventTypeData: ref({}),
      eventTypes: ref([]),
      eventSubTypes: ref([]),
      getEventTypeData: vi.fn().mockReturnValue(computed(() => undefined)),
      historyEventTypeGlobalMapping: ref({}),
    });
    const { connected } = storeToRefs(useMainStore());
    set(connected, true);
    useSupportedChains();
    await flushPromises();
  });

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should omit the date matchers when the period is disabled', () => {
    const { matchers } = useHistoryEventFilter({ period: true }, ref([HistoryEventEntryType.EVM_EVENT]));
    const keys = get(matchers).map(matcher => matcher.key);

    expect(keys).not.toContain('start');
    expect(keys).not.toContain('end');
  });

  it('should include the date matchers when the period is not disabled', () => {
    const { matchers } = useHistoryEventFilter({ period: false }, ref([HistoryEventEntryType.EVM_EVENT]));
    const keys = get(matchers).map(matcher => matcher.key);

    expect(keys).toContain('start');
    expect(keys).toContain('end');
  });

  it('should offer the entry-type matcher only when more than one entry type is in play', () => {
    const single = useHistoryEventFilter({}, ref([HistoryEventEntryType.EVM_EVENT]));
    expect(get(single.matchers).find(matcher => matcher.key === 'type')).toBeUndefined();

    const multiple = useHistoryEventFilter(
      {},
      ref([HistoryEventEntryType.EVM_EVENT, HistoryEventEntryType.HISTORY_EVENT]),
    );
    expect(get(multiple.matchers).find(matcher => matcher.key === 'type')).toBeDefined();

    const unrestricted = useHistoryEventFilter({}, ref(undefined));
    expect(get(unrestricted.matchers).find(matcher => matcher.key === 'type')).toBeDefined();
  });

  it('should include the transaction matchers only for transaction-bearing entry types', () => {
    const included = useHistoryEventFilter({}, ref([HistoryEventEntryType.EVM_EVENT]));
    const includedKeys = get(included.matchers).map(matcher => matcher.key);
    expect(includedKeys).toContain('tx_hash');
    expect(includedKeys).toContain('address');

    const excluded = useHistoryEventFilter({}, ref([HistoryEventEntryType.ASSET_MOVEMENT_EVENT]));
    const excludedKeys = get(excluded.matchers).map(matcher => matcher.key);
    expect(excludedKeys).not.toContain('tx_hash');
    expect(excludedKeys).not.toContain('address');
  });

  it('should keep the matchers in a stable display order', () => {
    const { matchers } = useHistoryEventFilter(
      {},
      ref([HistoryEventEntryType.EVM_EVENT, HistoryEventEntryType.ETH_WITHDRAWAL_EVENT]),
    );

    expect(get(matchers).map(matcher => matcher.key)).toEqual([
      'start',
      'end',
      'asset',
      'notes',
      'min_amount',
      'max_amount',
      'protocol',
      'location',
      'type',
      'event_type',
      'event_subtype',
      'tx_hash',
      'address',
      'validator_index',
    ]);
  });

  it('should include protocol matcher if protocols is not disabled and EVM events are included', () => {
    const { matchers } = useHistoryEventFilter(
      { protocols: false }, // Not disabled
      ref([HistoryEventEntryType.EVM_EVENT]),
    );
    const computedMatchers = get(matchers);

    // Ensure protocol matcher is present
    const protocolMatcher = computedMatchers.find(m => m.key === 'protocol');
    expect(protocolMatcher).toBeDefined();
    expect(protocolMatcher?.description).toContain('transactions.filter.protocol');
  });

  it('should exclude protocol matcher if protocols is disabled', () => {
    const { matchers } = useHistoryEventFilter(
      { protocols: true }, // protocols disabled
      ref([HistoryEventEntryType.EVM_EVENT]),
    );
    const computedMatchers = get(matchers);

    // Ensure protocol matcher is absent
    const protocolMatcher = computedMatchers.find(m => m.key === 'protocol');
    expect(protocolMatcher).toBeUndefined();
  });

  it('should include location matcher if locations is not disabled', () => {
    const { matchers } = useHistoryEventFilter(
      { locations: false },
      ref([HistoryEventEntryType.EVM_EVENT]),
    );
    const computedMatchers = get(matchers);

    // Ensure location matcher is present
    const locationMatcher = computedMatchers.find(m => m.key === 'location');
    expect(locationMatcher).toBeDefined();
    expect(locationMatcher?.description).toContain('transactions.filter.location');
  });

  it('should exclude location matcher if locations is disabled', () => {
    const { matchers } = useHistoryEventFilter(
      { locations: true },
      ref([HistoryEventEntryType.EVM_EVENT]),
    );
    const computedMatchers = get(matchers);

    // Ensure location matcher is absent
    const locationMatcher = computedMatchers.find(m => m.key === 'location');
    expect(locationMatcher).toBeUndefined();
  });

  it('should include event_type matcher if eventTypes is not disabled and EVM or online events are included', () => {
    const { matchers } = useHistoryEventFilter(
      { eventTypes: false },
      ref([HistoryEventEntryType.EVM_EVENT]),
    );
    const computedMatchers = get(matchers);

    // Ensure event_type is present
    const eventTypeMatcher = computedMatchers.find(m => m.key === 'event_type');
    expect(eventTypeMatcher).toBeDefined();
    expect(eventTypeMatcher?.description).toContain('transactions.filter.event_type');
  });

  it('should exclude event_type matcher if eventTypes is disabled', () => {
    const { matchers } = useHistoryEventFilter(
      { eventTypes: true },
      ref([HistoryEventEntryType.EVM_EVENT]),
    );
    const computedMatchers = get(matchers);

    // Ensure event_type is absent
    const eventTypeMatcher = computedMatchers.find(m => m.key === 'event_type');
    expect(eventTypeMatcher).toBeUndefined();
  });

  it('should include event_subtype matcher if eventSubtypes is not disabled and EVM or online events are included', () => {
    const { matchers } = useHistoryEventFilter(
      { eventSubtypes: false },
      ref([HistoryEventEntryType.EVM_EVENT]),
    );
    const computedMatchers = get(matchers);

    // Ensure event_subtype is present
    const eventSubtypeMatcher = computedMatchers.find(m => m.key === 'event_subtype');
    expect(eventSubtypeMatcher).toBeDefined();
    expect(eventSubtypeMatcher?.description).toContain('transactions.filter.event_subtype');
  });

  it('should exclude event_subtype matcher if eventSubtypes is disabled', () => {
    const { matchers } = useHistoryEventFilter(
      { eventSubtypes: true },
      ref([HistoryEventEntryType.EVM_EVENT]),
    );
    const computedMatchers = get(matchers);

    // Ensure event_subtype is absent
    const eventSubtypeMatcher = computedMatchers.find(m => m.key === 'event_subtype');
    expect(eventSubtypeMatcher).toBeUndefined();
  });

  it('should include validator_indices matcher if not disabled and validator events are included', () => {
    // Based on the composable, validator indices are included for certain event types (withdrawal, block, deposit)
    const { matchers } = useHistoryEventFilter(
      { validators: false },
      ref([HistoryEventEntryType.ETH_DEPOSIT_EVENT]),
    );
    const computedMatchers = get(matchers);

    const validatorMatcher = computedMatchers.find(m => m.key === 'validator_index');
    expect(validatorMatcher).toBeDefined();
    expect(validatorMatcher?.description).toContain('transactions.filter.validator_index');
  });

  it('should exclude validator_indices if disabled, even if validator events are included', () => {
    const { matchers } = useHistoryEventFilter(
      { validators: true },
      ref([HistoryEventEntryType.ETH_DEPOSIT_EVENT]),
    );
    const computedMatchers = get(matchers);

    const validatorMatcher = computedMatchers.find(m => m.key === 'validator_index');
    expect(validatorMatcher).toBeUndefined();
  });

  describe('date range validation', () => {
    // Use convertToTimestamp to get timestamps in the same timezone as the validator
    const earlyDate = '01/01/2023';
    const lateDate = '01/12/2023';

    function getTimestamp(date: string): string {
      return convertToTimestamp(date).toString();
    }

    it('should reject start date that is after the end date', () => {
      const { matchers, filters } = useHistoryEventFilter({});
      set(filters, { toTimestamp: getTimestamp(earlyDate) });

      const computedMatchers = get(matchers);
      const startMatcher = computedMatchers.find(m => m.key === 'start');
      assert(startMatcher && 'validate' in startMatcher);

      expect(startMatcher.validate(lateDate)).toBe(false);
    });

    it('should accept start date that is before the end date', () => {
      const { matchers, filters } = useHistoryEventFilter({});
      set(filters, { toTimestamp: getTimestamp(lateDate) });

      const computedMatchers = get(matchers);
      const startMatcher = computedMatchers.find(m => m.key === 'start');
      assert(startMatcher && 'validate' in startMatcher);

      expect(startMatcher.validate(earlyDate)).toBe(true);
    });

    it('should reject end date that is before the start date', () => {
      const { matchers, filters } = useHistoryEventFilter({});
      set(filters, { fromTimestamp: getTimestamp(lateDate) });

      const computedMatchers = get(matchers);
      const endMatcher = computedMatchers.find(m => m.key === 'end');
      assert(endMatcher && 'validate' in endMatcher);

      expect(endMatcher.validate(earlyDate)).toBe(false);
    });

    it('should accept end date that is after the start date', () => {
      const { matchers, filters } = useHistoryEventFilter({});
      set(filters, { fromTimestamp: getTimestamp(earlyDate) });

      const computedMatchers = get(matchers);
      const endMatcher = computedMatchers.find(m => m.key === 'end');
      assert(endMatcher && 'validate' in endMatcher);

      expect(endMatcher.validate(lateDate)).toBe(true);
    });

    it('should accept start or end date when no other bound is set', () => {
      const { matchers } = useHistoryEventFilter({});

      const computedMatchers = get(matchers);
      const startMatcher = computedMatchers.find(m => m.key === 'start');
      const endMatcher = computedMatchers.find(m => m.key === 'end');
      assert(startMatcher && 'validate' in startMatcher);
      assert(endMatcher && 'validate' in endMatcher);

      expect(startMatcher.validate(earlyDate)).toBe(true);
      expect(endMatcher.validate(lateDate)).toBe(true);
    });

    it('should reject a future start date', () => {
      const { matchers } = useHistoryEventFilter({});

      const computedMatchers = get(matchers);
      const startMatcher = computedMatchers.find(m => m.key === 'start');
      assert(startMatcher && 'validate' in startMatcher);

      expect(startMatcher.validate('01/01/2099')).toBe(false);
    });

    it('should reject a future end date', () => {
      const { matchers } = useHistoryEventFilter({});

      const computedMatchers = get(matchers);
      const endMatcher = computedMatchers.find(m => m.key === 'end');
      assert(endMatcher && 'validate' in endMatcher);

      expect(endMatcher.validate('01/01/2099')).toBe(false);
    });
  });

  describe('amount range validation', () => {
    it('should include the min and max amount matchers', () => {
      const { matchers } = useHistoryEventFilter({});
      const computedMatchers = get(matchers);

      const minAmountMatcher = computedMatchers.find(m => m.key === 'min_amount');
      const maxAmountMatcher = computedMatchers.find(m => m.key === 'max_amount');
      expect(minAmountMatcher).toBeDefined();
      expect(minAmountMatcher?.description).toContain('transactions.filter.min_amount');
      expect(maxAmountMatcher).toBeDefined();
      expect(maxAmountMatcher?.description).toContain('transactions.filter.max_amount');
    });

    it('should reject non-numeric or negative amounts', () => {
      const { matchers } = useHistoryEventFilter({});
      const computedMatchers = get(matchers);
      const minAmountMatcher = computedMatchers.find(m => m.key === 'min_amount');
      assert(minAmountMatcher && 'validate' in minAmountMatcher);

      expect(minAmountMatcher.validate('abc')).toBe(false);
      expect(minAmountMatcher.validate('-1')).toBe(false);
      expect(minAmountMatcher.validate('')).toBe(false);
    });

    it('should accept a numeric amount when no other bound is set', () => {
      const { matchers } = useHistoryEventFilter({});
      const computedMatchers = get(matchers);
      const minAmountMatcher = computedMatchers.find(m => m.key === 'min_amount');
      const maxAmountMatcher = computedMatchers.find(m => m.key === 'max_amount');
      assert(minAmountMatcher && 'validate' in minAmountMatcher);
      assert(maxAmountMatcher && 'validate' in maxAmountMatcher);

      expect(minAmountMatcher.validate('25')).toBe(true);
      expect(maxAmountMatcher.validate('30.5')).toBe(true);
    });

    it('should reject a min amount that is greater than the max amount', () => {
      const { matchers, filters } = useHistoryEventFilter({});
      set(filters, { maxAmount: '30' });

      const computedMatchers = get(matchers);
      const minAmountMatcher = computedMatchers.find(m => m.key === 'min_amount');
      assert(minAmountMatcher && 'validate' in minAmountMatcher);

      expect(minAmountMatcher.validate('31')).toBe(false);
      expect(minAmountMatcher.validate('25')).toBe(true);
    });

    it('should reject a max amount that is smaller than the min amount', () => {
      const { matchers, filters } = useHistoryEventFilter({});
      set(filters, { minAmount: '25' });

      const computedMatchers = get(matchers);
      const maxAmountMatcher = computedMatchers.find(m => m.key === 'max_amount');
      assert(maxAmountMatcher && 'validate' in maxAmountMatcher);

      expect(maxAmountMatcher.validate('24')).toBe(false);
      expect(maxAmountMatcher.validate('30')).toBe(true);
    });
  });

  describe('send selected location to asset search', () => {
    it('should pass the location string to assetSuggestions for chain sanitization', () => {
      const { matchers, filters } = useHistoryEventFilter({});
      set(filters, { location: 'kraken' });

      // Access matchers so that the computed function runs
      const computedMatchers = get(matchers);
      const assetMatcher = computedMatchers.find(m => 'asset' in m && m.asset);

      expect(assetMatcher).toBeDefined();

      // Location is passed through to assetSuggestions, which handles sanitization internally
      expect(assetSuggestions).toHaveBeenCalledWith(expect.anything(), 'kraken');
    });

    it('should pass the EVM chain location string to assetSuggestions', async () => {
      const { matchers, filters } = useHistoryEventFilter({});
      set(filters, { location: 'ethereum' });

      const computedMatchers = get(matchers);
      const assetMatcher = computedMatchers.find(m => 'asset' in m && m.asset);

      expect(assetMatcher).toBeDefined();

      await nextTick();

      // We expect the location to be passed through
      expect(assetSuggestions).toHaveBeenCalledWith(expect.anything(), 'ethereum');
    });

    it('should pass the Solana chain location string to assetSuggestions', async () => {
      const { matchers, filters } = useHistoryEventFilter({});
      set(filters, { location: 'solana' });

      const computedMatchers = get(matchers);
      const assetMatcher = computedMatchers.find(m => 'asset' in m && m.asset);

      expect(assetMatcher).toBeDefined();

      await nextTick();

      // We expect the Solana location to be passed through
      expect(assetSuggestions).toHaveBeenCalledWith(expect.anything(), 'solana');
    });
  });
});

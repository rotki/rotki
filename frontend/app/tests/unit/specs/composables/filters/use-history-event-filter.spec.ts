import { useHistoryEventFilter } from '@/composables/filters/events';
import { useSupportedChains } from '@/composables/info/chains';
import { useMainStore } from '@/store/main';
import { assetSuggestions } from '@/utils/assets';
import { HistoryEventEntryType } from '@rotki/common';
import { get } from '@vueuse/core';
import flushPromises from 'flush-promises';
import { createPinia, setActivePinia } from 'pinia';
import { beforeAll, beforeEach, describe, expect, it, vi } from 'vitest';
import { ref } from 'vue';

vi.mock('@/utils/assets', async () => {
  const mod = await vi.importActual<typeof import('@/utils/assets')>(
    '@/utils/assets',
  );
  return {
    ...mod,
    assetSuggestions: vi.fn().mockReturnValue([]),
  };
});

describe('composables::filter/use-history-event-filter - Additional Tests', () => {
  beforeAll(async () => {
    setActivePinia(createPinia());
    const { connected } = storeToRefs(useMainStore());
    set(connected, true);
    useSupportedChains();
    await flushPromises();
  });

  beforeEach(() => {
    vi.clearAllMocks();
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

  describe('send selected location to asset search if it\'s evm chain', () => {
    it('should pass undefined as second parameter to assetSuggestions when location is not an EVM chain', () => {
      const { matchers, filters } = useHistoryEventFilter({});
      set(filters, { location: 'kraken' });

      // Access matchers so that the computed function runs
      const computedMatchers = get(matchers);
      const assetMatcher = computedMatchers.find(m => 'asset' in m && m.asset);

      expect(assetMatcher).toBeDefined();

      // We expect the second argument to be undefined because "kraken" is not an EVM chain
      expect(assetSuggestions).toHaveBeenCalledWith(expect.anything(), undefined);
    });

    it('should pass the location string as second parameter to assetSuggestions when location is an EVM chain', async () => {
      const { matchers, filters } = useHistoryEventFilter({});
      set(filters, { location: 'ethereum' });

      const computedMatchers = get(matchers);
      const assetMatcher = computedMatchers.find(m => 'asset' in m && m.asset);

      expect(assetMatcher).toBeDefined();

      await nextTick();

      // We expect the second argument to be "ethereum"
      expect(assetSuggestions).toHaveBeenCalledWith(expect.anything(), 'ethereum');
    });
  });
});

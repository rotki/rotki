import type { FieldDef } from '@/modules/core/table/pill/core/types';
import type { HistoryEventsRestrictions } from '@/modules/history/events/history-events-restrictions';
import type { Filters } from '@/modules/history/events/use-events-filter';
import { HistoryEventEntryType } from '@rotki/common';
import { assert, beforeEach, describe, expect, it, vi } from 'vitest';
import { type Ref, ref } from 'vue';
import { useHistoryEventFields } from '@/modules/history/events/use-history-event-fields';

const {
  accountOptions,
  actionRows,
  assetSearch,
  assetSuggestions,
  associatedLocations,
  counterparties,
  typeMapping,
} = await vi.hoisted(
  async () => {
    const { ref } = await import('vue');
    return {
      accountOptions: ref<{ keywords?: string; loading?: boolean; value: string }[]>([]),
      actionRows: ref<{ direction: string; icon: string; label: string; verbKey: string }[]>([]),
      assetSearch: vi.fn(async () => []),
      assetSuggestions: vi.fn(() => async (): Promise<unknown[]> => []),
      associatedLocations: ref<string[]>([]),
      counterparties: ref<string[]>([]),
      typeMapping: ref<Record<string, Record<string, string>>>({}),
    };
  },
);

vi.mock('@/modules/history/events/mapping/use-history-event-mappings', async () => {
  const { computed } = await import('vue');
  return {
    useHistoryEventMappings: (): Record<string, unknown> => ({
      getHistoryEventSubTypeName: (value: string): string => value,
      getHistoryEventTypeName: (value: string): string => value,
      historyEventTypeGlobalMapping: computed(() => typeMapping.value),
      historyEventTypes: computed(() => Object.keys(typeMapping.value)),
    }),
  };
});

vi.mock('@/modules/history/events/mapping/use-history-event-counterparty-mappings', async () => {
  const { computed } = await import('vue');
  return {
    useHistoryEventCounterpartyMappings: (): Record<string, unknown> => ({
      counterparties: computed(() => counterparties.value),
    }),
  };
});

vi.mock('@/modules/history/use-account-filter-options', async () => {
  const { computed } = await import('vue');
  return {
    useAccountFilterOptions: (): Record<string, unknown> => ({
      options: computed(() => accountOptions.value),
      resolveCaption: (value: string): string => `caption:${value}`,
      resolveLabel: (value: string): string => `label:${value}`,
    }),
  };
});

vi.mock('@/modules/history/events/action-picker/use-event-action-picker', async () => {
  const { computed } = await import('vue');
  return {
    useEventActionPicker: (): Record<string, unknown> => ({
      rows: computed(() => actionRows.value),
    }),
  };
});

vi.mock('@/modules/assets/use-asset-info-retrieval', () => ({
  useAssetInfoRetrieval: (): Record<string, unknown> => ({ assetSearch }),
}));

/**
 * Replaced rather than driven: the real one returns a debounced search, so the scope it was built
 * with is only observable at build time.
 */
vi.mock('@/modules/core/common/display/assets', async (importOriginal) => {
  const actual = await importOriginal<Record<string, unknown>>();
  return { ...actual, assetSuggestions };
});

vi.mock('@/modules/history/use-history-store', async () => {
  const { computed, ref } = await import('vue');
  return {
    useHistoryStore: (): Record<string, unknown> => ({
      associatedLocations: computed(() => associatedLocations.value),
      undecodedTransactionsStatus: ref({}),
    }),
  };
});

/** `storeToRefs` would double-wrap the plain refs the store mock hands back. */
vi.mock('pinia', async (importOriginal) => {
  const actual = await importOriginal<Record<string, unknown>>();
  return {
    ...actual,
    storeToRefs: (store: Record<string, unknown>): Record<string, unknown> => store,
  };
});

function fields(
  restrictions: HistoryEventsRestrictions = {},
  modelFilters: Ref<Filters> = ref({}),
): FieldDef[] {
  return get(useHistoryEventFields({ modelFilters, restrictions }));
}

function keys(defs: FieldDef[]): string[] {
  return defs.map(def => def.key);
}

function field(defs: FieldDef[], key: string): FieldDef {
  const found = defs.find(def => def.key === key);
  assert(found);
  return found;
}

describe('useHistoryEventFields', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
    set(accountOptions, []);
    set(actionRows, []);
    set(associatedLocations, []);
    set(counterparties, []);
    set(typeMapping, {});
  });

  /**
   * A page pinned to one protocol, location, period, validator set or event type has already made
   * that choice for the user, so the bar has nothing left to offer a pill for.
   */
  describe('what the view has already fixed', () => {
    it('should offer every pill when nothing is pinned', () => {
      expect(keys(fields())).toContain('location');
      expect(keys(fields())).toContain('counterparties');
    });

    it('should drop the location pill on a page pinned to one location', () => {
      expect(keys(fields({ location: 'kraken' }))).not.toContain('location');
    });

    it('should drop the protocol pill on a page pinned to a protocol', () => {
      expect(keys(fields({ protocols: ['uniswap-v3'] }))).not.toContain('counterparties');
    });

    it('should drop the event type pill on a page pinned to event types', () => {
      expect(keys(fields({ eventTypes: ['deposit'] }))).not.toContain('eventTypes');
    });

    it('should drop the validator pill on a page pinned to validators', () => {
      expect(keys(fields({ validators: [12] }))).not.toContain('validatorIndices');
    });

    /** An empty restriction is not a restriction, so the pill stays. */
    it('should keep the protocol pill when the list is empty', () => {
      expect(keys(fields({ protocols: [] }))).toContain('counterparties');
    });
  });

  /** The view picks the accounts itself, so there is no account pill to offer. */
  describe('the account pill', () => {
    it('should be offered when the view leaves accounts to the user', () => {
      expect(keys(fields())).toContain('account');
    });

    it('should be dropped when the view pins the accounts', () => {
      const pinned = fields({ externalAccounts: [{ address: '0x0', chain: 'eth' }] });

      expect(keys(pinned)).not.toContain('account');
    });

    it('should keep the param pills either way', () => {
      const pinned = fields({ externalAccounts: [{ address: '0x0', chain: 'eth' }] });

      expect(keys(pinned)).toEqual(expect.arrayContaining(['action', 'state', 'ignored']));
    });
  });

  /**
   * The subtypes on offer follow the event types that are picked, so a narrowing prunes the ones it
   * stops admitting rather than leaving a subtype no event can have.
   */
  describe('the event subtypes on offer', () => {
    beforeEach(() => {
      set(typeMapping, {
        deposit: { 'deposit asset': 'in' },
        withdrawal: { 'remove asset': 'out' },
      });
    });

    it('should offer every subtype while no event type is picked', () => {
      const suggestions = field(fields(), 'eventSubtypes').suggest?.();

      expect(suggestions).toEqual(expect.arrayContaining(['deposit asset', 'remove asset']));
    });

    it('should offer only the subtypes of the picked event type', () => {
      const picked = ref<Filters>({ eventTypes: ['deposit'] });

      const suggestions = field(fields({}, picked), 'eventSubtypes').suggest?.();

      expect(suggestions).toEqual(['deposit asset']);
    });

    /** The bag types the picked types as one-or-many, so a lone pick is not a character array. */
    it('should read a single picked type as one type', () => {
      const picked = ref<Filters>({ eventTypes: 'deposit' });

      const suggestions = field(fields({}, picked), 'eventSubtypes').suggest?.();

      expect(suggestions).toEqual(['deposit asset']);
    });
  });

  /**
   * The asset search is scoped to the picked location, so a location that names a chain searches
   * that chain's assets rather than everything.
   */
  describe('the asset search', () => {
    async function search(picked: Filters): Promise<void> {
      await field(fields({}, ref<Filters>(picked)), 'asset').searchAsset?.('eth');
    }

    it('should search unscoped while no location is picked', async () => {
      await search({});

      expect(assetSuggestions).toHaveBeenCalledWith(assetSearch, undefined);
    });

    it('should scope the search to the picked location', async () => {
      await search({ location: 'optimism' });

      expect(assetSuggestions).toHaveBeenCalledWith(assetSearch, 'optimism');
    });

    /** The bag types the picked location as one-or-many, so a lone pick is not an array. */
    it('should read a single picked location as one location', async () => {
      await search({ location: ['optimism'] });

      expect(assetSuggestions).toHaveBeenCalledWith(assetSearch, 'optimism');
    });
  });

  describe('the account pill options', () => {
    beforeEach(() => {
      set(accountOptions, [
        { keywords: 'my wallet', loading: false, value: '0xaaa' },
        { loading: true, value: '0xbbb' },
      ]);
    });

    it('should offer every account it was given', () => {
      expect(field(fields(), 'account').suggest?.()).toEqual(['0xaaa', '0xbbb']);
    });

    it('should resolve the keywords of an account that has them', () => {
      expect(field(fields(), 'account').resolveKeywords?.('0xaaa')).toBe('my wallet');
    });

    it('should resolve no keywords for an account without them', () => {
      expect(field(fields(), 'account').resolveKeywords?.('0xbbb')).toBeUndefined();
    });

    /** An account whose name is still being resolved is marked, so its row can say so. */
    it('should report which accounts are still loading', () => {
      const account = field(fields(), 'account');

      expect(account.resolveLoading?.('0xbbb')).toBe(true);
      expect(account.resolveLoading?.('0xaaa')).toBe(false);
    });
  });

  it('should offer the locations the account has actually used', () => {
    set(associatedLocations, ['kraken', 'ethereum']);

    expect(field(fields(), 'location').suggest?.()).toEqual(['kraken', 'ethereum']);
  });

  it('should offer the known counterparties', () => {
    set(counterparties, ['uniswap-v3']);

    expect(field(fields(), 'counterparties').suggest?.()).toEqual(['uniswap-v3']);
  });

  /** A page admitting one entry type has nothing to choose between, so it gets no pill at all. */
  describe('the entry type pill', () => {
    it('should offer only the entry types the page admits', () => {
      const defs = fields({
        entryTypes: [HistoryEventEntryType.EVM_EVENT, HistoryEventEntryType.ETH_WITHDRAWAL_EVENT],
      });

      expect(field(defs, 'entryTypes').suggest?.())
        .toEqual([HistoryEventEntryType.EVM_EVENT, HistoryEventEntryType.ETH_WITHDRAWAL_EVENT]);
    });

    it('should offer every entry type when the page admits any', () => {
      expect(field(fields(), 'entryTypes').suggest?.()).toEqual(Object.values(HistoryEventEntryType));
    });

    it('should be dropped when the page admits a single entry type', () => {
      expect(keys(fields({ entryTypes: [HistoryEventEntryType.EVM_EVENT] }))).not.toContain('entryTypes');
    });
  });
});

import type { EffectScope, MaybeRefOrGetter, Ref } from 'vue';
import type { BlockchainAccount } from '@/modules/accounts/blockchain-accounts';
import type { CalendarEvent } from '@/modules/calendar/types';
import type { Collection } from '@/modules/core/common/collection';
import { flushPromises } from '@vue/test-utils';
import dayjs from 'dayjs';
import { createPinia, setActivePinia } from 'pinia';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { useCalendarData } from './use-calendar-data';

interface ParamSource {
  values: MaybeRefOrGetter<Record<string, unknown>>;
  to: 'request' | 'url' | 'both';
  fromQuery?: (query: Record<string, unknown>) => void;
  skipEmpty?: boolean;
  isDefault?: boolean;
}

interface ServerTableOptions {
  params?: ParamSource[];
}

let captured: ServerTableOptions = {};

/**
 * Looks a source up by a key it is expected to carry, not by destination alone:
 * there is more than one `request` source, so destination is ambiguous.
 */
function sourceValues(destination: 'request' | 'url' | 'both', key: string): Record<string, unknown> {
  const source = captured.params?.find(item => item.to === destination && key in toValue(item.values));
  expect(source).toBeDefined();
  return toValue(source!.values);
}

/** Runs the read direction of the source that carries `key` at `destination`. */
function applySourceRead(destination: 'request' | 'url' | 'both', key: string, query: Record<string, unknown>): void {
  const source = captured.params?.find(item => item.to === destination && key in toValue(item.values));
  expect(source?.fromQuery).toBeDefined();
  source!.fromQuery!(query);
}
const state = ref<Collection<CalendarEvent>>({ data: [], found: 0, limit: 10, total: 0 });
const pagination = ref({ limit: 10, limits: [10], page: 1, total: 0 });
const isLoading = ref<boolean>(false);
const fetchData = vi.fn().mockResolvedValue(undefined);
const fetchCalendarEvents = vi.fn();
const getAccountByAddress = vi.fn();

vi.mock('@/modules/core/table/use-server-table', () => ({
  useServerTable: vi.fn((options: ServerTableOptions) => {
    captured = options;
    return {
      collection: state,
      filter: computed(() => ({})),
      isLoading,
      matchers: computed(() => []),
      pagination,
      refetch: fetchData,
      setFilter: vi.fn(),
      setPage: vi.fn(),
      sort: computed(() => ({ column: undefined, direction: 'asc' as const })),
    };
  }),
}));

vi.mock('@/modules/calendar/use-calendar-api', () => ({
  useCalendarApi: vi.fn(() => ({ fetchCalendarEvents })),
}));

vi.mock('@/modules/accounts/use-blockchain-accounts-store', () => ({
  useBlockchainAccountsStore: vi.fn(() => ({ getAccountByAddress })),
}));

function makeAccount(address: string, chain: string): BlockchainAccount {
  return { chain, data: { address, type: 'address' }, nativeAsset: 'ETH' };
}

function makeEvent(overrides: Partial<CalendarEvent> = {}): CalendarEvent {
  return { autoDelete: false, identifier: 1, name: 'evt', timestamp: 1700000000, ...overrides };
}

describe('useCalendarData', () => {
  let scope: EffectScope;

  // Run each instance inside an owned effect scope so its watchers are disposed
  // in afterEach. Otherwise watchers on the shared module-level `state` ref leak
  // across tests and fire on later `set(state, ...)` mutations.
  function createCalendarData(accounts: Ref<BlockchainAccount[]>): ReturnType<typeof useCalendarData> {
    return scope.run(() => useCalendarData(accounts))!;
  }

  beforeEach(() => {
    scope = effectScope();
    setActivePinia(createPinia());
    vi.clearAllMocks();
    captured = {};
    set(state, { data: [], found: 0, limit: 10, total: 0 });
    set(pagination, { limit: 10, limits: [10], page: 1, total: 0 });
    set(isLoading, false);
    fetchCalendarEvents.mockResolvedValue({ data: [], found: 0, limit: 5, total: 0 });
    fetchData.mockResolvedValue(undefined);
  });

  afterEach(() => {
    scope.stop();
    vi.useRealTimers();
  });

  it('should expose state, pagination and isLoading from useServerTable', () => {
    const accounts = ref<BlockchainAccount[]>([]);
    const result = createCalendarData(accounts);

    expect(result.events).toBe(state);
    expect(result.pagination).toBe(pagination);
    expect(result.isLoading).toBe(isLoading);
    expect(result.dateFormat).toBe('YYYY-MM-DD');
  });

  it('should compute eventsWithDate by formatting the timestamp', () => {
    const accounts = ref<BlockchainAccount[]>([]);
    const { eventsWithDate } = createCalendarData(accounts);

    set(state, {
      data: [makeEvent()],
      found: 1,
      limit: 10,
      total: 1,
    });

    const formatted = get(eventsWithDate);
    expect(formatted[0].date).toBe(dayjs(1700000000 * 1000).format('YYYY-MM-DD'));
  });

  it('should setToday update the today ref and return the new dayjs', () => {
    const accounts = ref<BlockchainAccount[]>([]);
    const { setToday, today } = createCalendarData(accounts);

    const before = get(today);
    const next = setToday();

    expect(next.isSame(get(today))).toBe(true);
    expect(next.valueOf()).toBeGreaterThanOrEqual(before.valueOf());
  });

  it('should initializePagination set limit=-1 and trigger fetchData', () => {
    const accounts = ref<BlockchainAccount[]>([]);
    const { initializePagination } = createCalendarData(accounts);

    initializePagination();

    expect(get(pagination).limit).toBe(-1);
    expect(fetchData).toHaveBeenCalled();
  });

  describe('options to useServerTable', () => {
    it('should pass extraParams with address#chain entries', async () => {
      vi.useFakeTimers();
      const accounts = ref<BlockchainAccount[]>([makeAccount('0xabc', 'eth'), makeAccount('0xdef', 'optimism')]);
      const { modelRange } = createCalendarData(accounts);

      set(modelRange, [100, 200]);
      // `refDebounced(modelRange, 300)` — drive the debounce instead of sleeping
      await vi.advanceTimersByTimeAsync(300);

      // Accounts are shareable and round-trip through the URL.
      expect(sourceValues('both', 'accounts').accounts).toEqual(['0xabc#eth', '0xdef#optimism']);

      // The visible range is request-only: it is a viewport, not a filter, and would
      // otherwise add a history entry per month stepped through.
      const rangeValues = sourceValues('request', 'fromTimestamp');
      expect(rangeValues.fromTimestamp).toBe('100');
      expect(rangeValues.toTimestamp).toBe('200');
    });

    it('should keep the date range out of the url', () => {
      const accounts = ref<BlockchainAccount[]>([makeAccount('0xabc', 'eth')]);
      createCalendarData(accounts);

      const urlBound = (captured.params ?? []).filter(item => item.to === 'both' || item.to === 'url');
      for (const source of urlBound) {
        const values = toValue(source.values);
        expect(values).not.toHaveProperty('fromTimestamp');
        expect(values).not.toHaveProperty('toTimestamp');
      }
    });

    it('should build requestParams with blockchain when chain is a known blockchain', () => {
      const accounts = ref<BlockchainAccount[]>([makeAccount('0xabc', 'eth')]);
      createCalendarData(accounts);

      const params = sourceValues('request', 'accounts');
      expect(params.accounts).toEqual([{ address: '0xabc', blockchain: 'eth' }]);
    });

    it('should omit blockchain when chain is ALL or not a blockchain', () => {
      const accounts = ref<BlockchainAccount[]>([makeAccount('0xabc', 'ALL'), makeAccount('0xdef', 'banana')]);
      createCalendarData(accounts);

      const params = sourceValues('request', 'accounts');
      expect(params.accounts).toEqual([
        { address: '0xabc' },
        { address: '0xdef' },
      ]);
    });

    it('should leave requestParams.accounts undefined when no accounts are selected', () => {
      const accounts = ref<BlockchainAccount[]>([]);
      createCalendarData(accounts);

      // With no accounts selected the request source is empty, so it cannot be found
      // by key; identify it as the request source that is not the date range.
      const source = (captured.params ?? []).find(
        item => item.to === 'request' && !('fromTimestamp' in toValue(item.values)),
      );
      expect(source).toBeDefined();
      expect(toValue(source!.values).accounts).toBeUndefined();
    });

    it('should reset accounts when the route carries no accounts', () => {
      const accounts = ref<BlockchainAccount[]>([makeAccount('0xabc', 'eth')]);
      createCalendarData(accounts);

      applySourceRead('both', 'accounts', {});
      expect(get(accounts)).toEqual([]);
    });

    it('should map parsed accounts via getAccountByAddress on route read', () => {
      const accounts = ref<BlockchainAccount[]>([]);
      const fetched = makeAccount('0xabc', 'eth');
      getAccountByAddress.mockReturnValue(fetched);
      createCalendarData(accounts);

      applySourceRead('both', 'accounts', { accounts: '0xabc#eth' });

      expect(getAccountByAddress).toHaveBeenCalledWith('0xabc', 'eth');
      expect(get(accounts)).toEqual([fetched]);
    });
  });

  describe('upcoming events watcher', () => {
    it('should slice the first 5 upcoming events when state already has 5+', async () => {
      const accounts = ref<BlockchainAccount[]>([]);
      const { upcomingEvents } = createCalendarData(accounts);

      const future = dayjs().add(1, 'day').unix();
      const items: CalendarEvent[] = Array.from({ length: 7 }, (_, i) => makeEvent({
        identifier: i + 1,
        name: `evt-${i + 1}`,
        timestamp: future + i,
      }));

      set(state, { data: items, found: items.length, limit: 10, total: items.length });
      await flushPromises();

      expect(get(upcomingEvents)).toHaveLength(5);
      expect(fetchCalendarEvents).not.toHaveBeenCalled();
    });

    it('should fetch a fresh batch when fewer than 5 future events exist', async () => {
      const accounts = ref<BlockchainAccount[]>([]);
      const apiResponse = {
        data: [makeEvent({ name: 'api-evt', timestamp: 1 })],
        found: 1,
        limit: 5,
        total: 1,
      };
      fetchCalendarEvents.mockResolvedValue(apiResponse);

      const { upcomingEvents } = createCalendarData(accounts);
      await flushPromises();

      // Trigger watcher with a state change so the latest resolve wins
      set(state, { data: [], found: 0, limit: 10, total: 1 });
      await flushPromises();

      expect(fetchCalendarEvents).toHaveBeenCalled();
      expect(get(upcomingEvents)).toEqual(apiResponse.data);
    });
  });
});

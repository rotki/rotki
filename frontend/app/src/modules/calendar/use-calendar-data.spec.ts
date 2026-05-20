import type { ComputedRef } from 'vue';
import type { BlockchainAccount } from '@/modules/accounts/blockchain-accounts';
import type { CalendarEvent, CalendarEventRequestPayload } from '@/modules/calendar/types';
import type { Collection } from '@/modules/core/common/collection';
import { flushPromises } from '@vue/test-utils';
import dayjs from 'dayjs';
import { createPinia, setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useCalendarData } from './use-calendar-data';

interface PaginationOptions {
  extraParams?: ComputedRef<Record<string, unknown>>;
  requestParams?: ComputedRef<Partial<CalendarEventRequestPayload>>;
  onUpdateFilters?: (query: Record<string, unknown>) => void;
}

let captured: PaginationOptions = {};
const state = ref<Collection<CalendarEvent>>({ data: [], found: 0, limit: 10, total: 0 });
const pagination = ref({ limit: 10, limits: [10], page: 1, total: 0 });
const isLoading = ref<boolean>(false);
const fetchData = vi.fn().mockResolvedValue(undefined);
const fetchCalendarEvents = vi.fn();
const getAccountByAddress = vi.fn();

vi.mock('@/modules/core/table/use-pagination-filter', () => ({
  usePaginationFilters: vi.fn((_req: unknown, options: PaginationOptions) => {
    captured = options;
    return {
      fetchData,
      filters: computed(() => ({})),
      isLoading,
      matchers: computed(() => []),
      pagination,
      setPage: vi.fn(),
      sort: computed(() => ({ column: undefined, direction: 'asc' as const })),
      state,
      updateFilter: vi.fn(),
      userAction: ref(false),
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
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
    captured = {};
    set(state, { data: [], found: 0, limit: 10, total: 0 });
    set(pagination, { limit: 10, limits: [10], page: 1, total: 0 });
    set(isLoading, false);
    fetchCalendarEvents.mockResolvedValue({ data: [], found: 0, limit: 5, total: 0 });
    fetchData.mockResolvedValue(undefined);
  });

  it('should expose state, pagination and isLoading from usePaginationFilters', () => {
    const accounts = ref<BlockchainAccount[]>([]);
    const result = useCalendarData(accounts);

    expect(result.events).toBe(state);
    expect(result.pagination).toBe(pagination);
    expect(result.isLoading).toBe(isLoading);
    expect(result.dateFormat).toBe('YYYY-MM-DD');
  });

  it('should compute eventsWithDate by formatting the timestamp', () => {
    const accounts = ref<BlockchainAccount[]>([]);
    const { eventsWithDate } = useCalendarData(accounts);

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
    const { setToday, today } = useCalendarData(accounts);

    const before = get(today);
    const next = setToday();

    expect(next.isSame(get(today))).toBe(true);
    expect(next.valueOf()).toBeGreaterThanOrEqual(before.valueOf());
  });

  it('should initializePagination set limit=-1 and trigger fetchData', () => {
    const accounts = ref<BlockchainAccount[]>([]);
    const { initializePagination } = useCalendarData(accounts);

    initializePagination();

    expect(get(pagination).limit).toBe(-1);
    expect(fetchData).toHaveBeenCalled();
  });

  describe('options to usePaginationFilters', () => {
    it('should pass extraParams with address#chain entries', async () => {
      const accounts = ref<BlockchainAccount[]>([makeAccount('0xabc', 'eth'), makeAccount('0xdef', 'optimism')]);
      const { range } = useCalendarData(accounts);

      set(range, [100, 200]);
      // debounced by 300ms — use fake timers to flush
      await new Promise(resolve => setTimeout(resolve, 320));

      const params = get(captured.extraParams!);
      expect(params.accounts).toEqual(['0xabc#eth', '0xdef#optimism']);
      expect(params.fromTimestamp).toBe('100');
      expect(params.toTimestamp).toBe('200');
    });

    it('should build requestParams with blockchain when chain is a known blockchain', () => {
      const accounts = ref<BlockchainAccount[]>([makeAccount('0xabc', 'eth')]);
      useCalendarData(accounts);

      const params = get(captured.requestParams!);
      expect(params.accounts).toEqual([{ address: '0xabc', blockchain: 'eth' }]);
    });

    it('should omit blockchain when chain is ALL or not a blockchain', () => {
      const accounts = ref<BlockchainAccount[]>([makeAccount('0xabc', 'ALL'), makeAccount('0xdef', 'banana')]);
      useCalendarData(accounts);

      const params = get(captured.requestParams!);
      expect(params.accounts).toEqual([
        { address: '0xabc' },
        { address: '0xdef' },
      ]);
    });

    it('should leave requestParams.accounts undefined when no accounts are selected', () => {
      const accounts = ref<BlockchainAccount[]>([]);
      useCalendarData(accounts);

      const params = get(captured.requestParams!);
      expect(params.accounts).toBeUndefined();
    });

    it('should reset accounts when onUpdateFilters receives no accounts', () => {
      const accounts = ref<BlockchainAccount[]>([makeAccount('0xabc', 'eth')]);
      useCalendarData(accounts);

      captured.onUpdateFilters?.({});
      expect(get(accounts)).toEqual([]);
    });

    it('should map parsed accounts via getAccountByAddress on onUpdateFilters', () => {
      const accounts = ref<BlockchainAccount[]>([]);
      const fetched = makeAccount('0xabc', 'eth');
      getAccountByAddress.mockReturnValue(fetched);
      useCalendarData(accounts);

      captured.onUpdateFilters?.({ accounts: '0xabc#eth' });

      expect(getAccountByAddress).toHaveBeenCalledWith('0xabc', 'eth');
      expect(get(accounts)).toEqual([fetched]);
    });
  });

  describe('upcoming events watcher', () => {
    it('should slice the first 5 upcoming events when state already has 5+', async () => {
      const accounts = ref<BlockchainAccount[]>([]);
      const { upcomingEvents } = useCalendarData(accounts);

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

      const { upcomingEvents } = useCalendarData(accounts);
      await flushPromises();

      // Trigger watcher with a state change so the latest resolve wins
      set(state, { data: [], found: 0, limit: 10, total: 1 });
      await flushPromises();

      expect(fetchCalendarEvents).toHaveBeenCalled();
      expect(get(upcomingEvents)).toEqual(apiResponse.data);
    });
  });
});

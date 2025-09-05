import type { Writeable } from '@rotki/common';
import type { TablePaginationData } from '@rotki/ui-library';
import type { ComputedRef, Ref } from 'vue';
import type { BlockchainAccount } from '@/types/blockchain/accounts';
import type { Collection } from '@/types/collection';
import type { CalendarEvent, CalendarEventRequestPayload } from '@/types/history/calendar';
import { startPromise } from '@shared/utils';
import dayjs, { type Dayjs } from 'dayjs';
import { isEqual } from 'es-toolkit';
import { useCalendarApi } from '@/composables/history/calendar';
import { usePaginationFilters } from '@/composables/use-pagination-filter';
import { useBlockchainAccountsStore } from '@/modules/accounts/use-blockchain-accounts-store';
import { isBlockchain } from '@/types/blockchain/chains';
import { RouterAccountsSchema } from '@/types/route';
import { getAccountAddress } from '@/utils/blockchain/accounts/utils';

interface UseCalendarDataReturn {
  dateFormat: string;
  events: Ref<Collection<CalendarEvent>>;
  eventsWithDate: ComputedRef<(CalendarEvent & { date: string })[]>;
  fetchData: () => Promise<void>;
  initializePagination: () => void;
  isLoading: Ref<boolean>;
  pagination: Ref<TablePaginationData>;
  range: Ref<[number, number]>;
  setToday: () => Dayjs;
  today: Ref<Dayjs>;
  upcomingEvents: Ref<CalendarEvent[]>;
}

export function useCalendarData(accounts: Ref<BlockchainAccount[]>): UseCalendarDataReturn {
  const { fetchCalendarEvents } = useCalendarApi();
  const { getAccountByAddress } = useBlockchainAccountsStore();

  const today = ref<Dayjs>(dayjs());
  const range = ref<[number, number]>([0, 0]);
  const rangeDebounced = refDebounced(range, 300);
  const upcomingEvents = ref<CalendarEvent[]>([]);

  const extraParams = computed<{ accounts: string[]; fromTimestamp: string; toTimestamp: string }>(() => {
    const rangeVal = get(rangeDebounced);
    return {
      accounts: get(accounts).map(account => `${getAccountAddress(account)}#${account.chain}`),
      fromTimestamp: rangeVal[0].toString(),
      toTimestamp: rangeVal[1].toString(),
    };
  });

  const {
    fetchData,
    isLoading,
    pagination,
    state: events,
  } = usePaginationFilters<
    CalendarEvent,
    CalendarEventRequestPayload
  >(fetchCalendarEvents, {
    defaultSortBy: {
      direction: 'asc',
    },
    extraParams,
    onUpdateFilters(query) {
      const parsedAccounts = RouterAccountsSchema.parse(query);
      const accountsParsed = parsedAccounts.accounts;
      if (!accountsParsed || accountsParsed.length === 0) {
        set(accounts, []);
      }
      else {
        set(
          accounts,
          accountsParsed.map(({ address, chain }) => getAccountByAddress(address, chain)),
        );
      }
    },
    requestParams: computed<Partial<CalendarEventRequestPayload>>(() => {
      const params: Writeable<Partial<CalendarEventRequestPayload>> = {};
      const accountsVal = get(accounts);

      if (accountsVal.length > 0) {
        params.accounts = accountsVal.map((account) => {
          const chain = account.chain;
          return {
            address: getAccountAddress(account),
            ...(chain !== 'ALL' && isBlockchain(chain) ? { blockchain: chain } : {}),
          };
        });
      }

      return params;
    }),
  });

  const dateFormat = 'YYYY-MM-DD';

  const eventsWithDate = computed<(CalendarEvent & { date: string })[]>(() =>
    get(events).data.map(item => ({
      ...item,
      date: dayjs(item.timestamp * 1000).format(dateFormat),
    })),
  );

  function initializePagination(): void {
    set(pagination, {
      ...get(pagination),
      limit: -1,
    });
    startPromise(fetchData());
  }

  function setToday(): Dayjs {
    const now = dayjs();
    set(today, now);
    return now;
  }

  // Watch for upcoming events
  watch([events, today], async ([events, today], [oldEvents, oldToday]) => {
    if (isEqual(events, oldEvents) && isEqual(today, oldToday))
      return;

    const upcomingEventsData = events.data.filter((item) => {
      const date = dayjs(item.timestamp * 1000);
      return date.isAfter(today);
    });

    if (upcomingEventsData.length >= 5) {
      set(upcomingEvents, upcomingEventsData.slice(0, 5));
    }
    else {
      const data = await fetchCalendarEvents({
        ascending: [true],
        fromTimestamp: today.add(1, 'day').startOf('day').unix(),
        limit: 5,
        offset: 0,
        orderByAttributes: ['timestamp'],
      });
      set(upcomingEvents, data.data);
    }
  });

  return {
    dateFormat,
    events,
    eventsWithDate,
    fetchData,
    initializePagination,
    isLoading,
    pagination,
    range,
    setToday,
    today,
    upcomingEvents,
  };
}

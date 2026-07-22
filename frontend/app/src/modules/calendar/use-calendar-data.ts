import type { Writeable } from '@rotki/common';
import type { TablePaginationData } from '@rotki/ui-library';
import type { ComputedRef, DeepReadonly, Ref } from 'vue';
import type { BlockchainAccount } from '@/modules/accounts/blockchain-accounts';
import type { CalendarEvent, CalendarEventRequestPayload } from '@/modules/calendar/types';
import type { Collection } from '@/modules/core/common/collection';
import { startPromise } from '@shared/utils';
import dayjs, { type Dayjs } from 'dayjs';
import { isEqual } from 'es-toolkit';
import { getAccountAddress } from '@/modules/accounts/account-utils';
import { useBlockchainAccountsStore } from '@/modules/accounts/use-blockchain-accounts-store';
import { useCalendarApi } from '@/modules/calendar/use-calendar-api';
import { isBlockchain } from '@/modules/core/common/chains';
import { RouterAccountsSchema } from '@/modules/core/table/route';
import { useServerTable } from '@/modules/core/table/use-server-table';

interface UseCalendarDataReturn {
  dateFormat: string;
  events: Ref<Collection<CalendarEvent>>;
  eventsWithDate: ComputedRef<(CalendarEvent & { date: string })[]>;
  fetchData: () => Promise<void>;
  initializePagination: () => void;
  isLoading: Ref<boolean>;
  pagination: Ref<TablePaginationData>;
  modelRange: Ref<[number, number]>;
  setToday: () => Dayjs;
  today: DeepReadonly<Ref<Dayjs>>;
  upcomingEvents: Readonly<Ref<CalendarEvent[]>>;
}

export function useCalendarData(accounts: Ref<BlockchainAccount[]>): UseCalendarDataReturn {
  const { fetchCalendarEvents } = useCalendarApi();
  const { getAccountByAddress } = useBlockchainAccountsStore();

  const today = ref<Dayjs>(dayjs());
  const modelRange = ref<[number, number]>([0, 0]);
  const rangeDebounced = refDebounced(modelRange, 300);
  const upcomingEvents = ref<CalendarEvent[]>([]);

  /**
   * Shareable: which accounts the calendar is filtered to. Round-trips through the
   * URL, and the source's `fromQuery` below reads it back.
   */
  const accountParams = computed<{ accounts: string[] }>(() => ({
    accounts: get(accounts).map(account => `${getAccountAddress(account)}#${account.chain}`),
  }));

  /**
   * Request-only: the visible date range is a viewport, not a filter. It changes on
   * every month navigation, so putting it in the URL would add a history entry per
   * month stepped through.
   */
  const rangeParams = computed<{ fromTimestamp: string; toTimestamp: string }>(() => {
    const rangeVal = get(rangeDebounced);
    return {
      fromTimestamp: rangeVal[0].toString(),
      toTimestamp: rangeVal[1].toString(),
    };
  });

  const requestParams = computed<Record<string, unknown>>(() => {
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
  });

  const {
    collection: events,
    isLoading,
    pagination,
    refetch: fetchData,
  } = useServerTable<
    CalendarEvent,
    CalendarEventRequestPayload
  >({
    fetch: fetchCalendarEvents,
    params: [
      {
        fromQuery(query): void {
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
        to: 'both',
        values: accountParams,
      },
      { to: 'request', values: rangeParams },
      { skipEmpty: true, to: 'request', values: requestParams },
    ],
    sort: {
      default: {
        direction: 'asc',
      },
    },
    urlState: { mode: 'route' },
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
    modelRange,
    setToday,
    today: readonly(today),
    upcomingEvents: shallowReadonly(upcomingEvents),
  };
}

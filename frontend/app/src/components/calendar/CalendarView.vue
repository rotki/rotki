<script setup lang="ts">
import type { AddressData, BlockchainAccount } from '@/types/blockchain/accounts';
import type { CalendarEvent, CalendarEventRequestPayload } from '@/types/history/calendar';
import type { Writeable } from '@rotki/common';
import CalendarDateNavigator from '@/components/calendar/CalendarDateNavigator.vue';
import CalendarEventList from '@/components/calendar/CalendarEventList.vue';
import CalendarFormDialog from '@/components/calendar/CalendarFormDialog.vue';
import CalendarGrid from '@/components/calendar/CalendarGrid.vue';
import CalendarMonthNavigator from '@/components/calendar/CalendarMonthNavigator.vue';
import CalendarSettingsMenu from '@/components/calendar/CalendarSettingsMenu.vue';
import CalendarUpcomingEventList from '@/components/calendar/CalendarUpcomingEventList.vue';
import DateDisplay from '@/components/display/DateDisplay.vue';
import BlockchainAccountSelector from '@/components/helper/BlockchainAccountSelector.vue';
import HistoryTableActions from '@/components/history/HistoryTableActions.vue';
import TablePageLayout from '@/components/layout/TablePageLayout.vue';
import { useCalendarApi } from '@/composables/history/calendar';
import { usePaginationFilters } from '@/composables/use-pagination-filter';
import { useBlockchainAccountsStore } from '@/modules/accounts/use-blockchain-accounts-store';
import { useConfirmStore } from '@/store/confirm';
import { useMessageStore } from '@/store/message';
import { useGeneralSettingsStore } from '@/store/settings/general';
import { isBlockchain } from '@/types/blockchain/chains';
import { RouterAccountsSchema } from '@/types/route';
import { getAccountAddress } from '@/utils/blockchain/accounts/utils';
import dayjs, { type Dayjs } from 'dayjs';
import { isEqual, omit } from 'es-toolkit';

const { t } = useI18n({ useScope: 'global' });

const selectedDate = ref<Dayjs>(dayjs());
const visibleDate = ref<Dayjs>(dayjs());

const today = ref<Dayjs>(dayjs());
const range = ref<[number, number]>([0, 0]);
const selectedDateEvents = ref<CalendarEvent[]>([]);
const upcomingEvents = ref<CalendarEvent[]>([]);
const accounts = ref<BlockchainAccount<AddressData>[]>([]);
const modelValue = ref<CalendarEvent>();
const editMode = ref<boolean>(false);

const { deleteCalendarEvent, fetchCalendarEvents } = useCalendarApi();
const { getAccountByAddress } = useBlockchainAccountsStore();
const { autoDeleteCalendarEntries } = storeToRefs(useGeneralSettingsStore());

function emptyEventForm() {
  const startOfTheDate = selectedDate.value.set('hours', 0).set('minutes', 0).set('seconds', 0);
  const timestamp = startOfTheDate.unix();

  return {
    address: undefined,
    autoDelete: get(autoDeleteCalendarEntries),
    blockchain: undefined,
    color: '',
    counterparty: undefined,
    description: '',
    identifier: 0,
    name: '',
    timestamp,
  };
}

const extraParams = computed(() => {
  const rangeVal = get(range);
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

onMounted(() => {
  set(pagination, {
    ...get(pagination),
    limit: -1,
  });
  fetchData();
});

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

const dateFormat = 'YYYY-MM-DD';

const eventsWithDate = computed(() =>
  get(events).data.map(item => ({
    ...item,
    date: dayjs(item.timestamp * 1000).format(dateFormat),
  })),
);

function setSelectedDate(day: Dayjs) {
  set(selectedDate, day);
}

function setToday() {
  const now = dayjs();
  set(today, now);
  setSelectedDate(now);
}

function add() {
  set(modelValue, emptyEventForm());
  set(editMode, false);
}

function edit(event: CalendarEvent & { date?: string }) {
  set(modelValue, omit(event, ['date']));
  set(editMode, true);
}

const { show } = useConfirmStore();
const { setMessage } = useMessageStore();

async function deleteClicked() {
  const item = get(modelValue);
  if (item) {
    try {
      await deleteCalendarEvent(item.identifier);
      await fetchData();
      set(modelValue, null);
    }
    catch (error: any) {
      setMessage({
        description: t('calendar.delete_error.message', { message: error.message }),
        success: false,
        title: t('calendar.delete_event'),
      });
    }
  }
}

function deleteEvent() {
  show(
    {
      message: t('calendar.dialog.delete.message'),
      title: t('calendar.delete_event'),
    },
    deleteClicked,
  );
}

watch(selectedDate, (selected) => {
  set(visibleDate, selected);
});

watch([selectedDate, eventsWithDate], ([selectedDate, eventsWithDate]) => {
  const selectedDateFormatted = selectedDate.format(dateFormat);
  const events = eventsWithDate.filter(item => item.date === selectedDateFormatted);
  if (events.length === 0 && selectedDateFormatted !== get(visibleDate).format(dateFormat))
    return;

  set(selectedDateEvents, events);
});

const route = useRoute();
const router = useRouter();

onMounted(async () => {
  const query = get(route).query;

  if (query.timestamp) {
    const timestamp = Number(query.timestamp);
    const date = dayjs(timestamp * 1000);
    if (date.isValid())
      set(selectedDate, date);

    await router.replace({ query: {} });
  }
});
</script>

<template>
  <TablePageLayout :title="[t('navigation_menu.calendar')]">
    <template #buttons>
      <CalendarSettingsMenu />
      <RuiButton
        color="primary"
        @click="add()"
      >
        <template #prepend>
          <RuiIcon name="lu-plus" />
        </template>
        {{ t('calendar.add_event') }}
      </RuiButton>
    </template>

    <div class="grid items-start grid-cols-[minmax(0,1fr)_14rem] gap-4">
      <RuiCard class="h-auto">
        <HistoryTableActions>
          <template #filter>
            <BlockchainAccountSelector
              v-model="accounts"
              class="md:w-[24rem]"
              multichain
              dense
              outlined
            />
          </template>
          <div class="flex gap-4">
            <CalendarMonthNavigator v-model="visibleDate" />
            <CalendarDateNavigator
              v-model="selectedDate"
              :visible-date="visibleDate"
              :today="today"
              @set-today="setToday()"
            />
          </div>
        </HistoryTableActions>
        <CalendarGrid
          :today="today"
          :selected-date="selectedDate"
          :visible-date="visibleDate"
          :events-with-date="eventsWithDate"
          @update:selected-date="setSelectedDate($event)"
          @update:range="range = $event"
          @edit="edit($event)"
          @add="add()"
        />

        <CalendarFormDialog
          v-model="modelValue"
          :loading="isLoading"
          :selected-date="selectedDate"
          :edit-mode="editMode"
          @delete="deleteEvent()"
          @refresh="fetchData()"
        />
      </RuiCard>
      <div class="flex flex-col gap-4 h-auto">
        <RuiCard class="[&>div:last-child]:!pt-2">
          <template #header>
            <div v-if="today.isSame(selectedDate, 'day')">
              {{ t('calendar.today_events') }}
            </div>
            <div v-else>
              <DateDisplay
                :timestamp="selectedDate.unix()"
                no-time
                hide-tooltip
              />
              {{ t('common.events') }}
            </div>
          </template>
          <div
            v-if="selectedDateEvents.length > 0"
            class="flex flex-col gap-4"
          >
            <CalendarEventList
              v-for="event in selectedDateEvents"
              :key="event.identifier"
              v-model:selected-date="selectedDate"
              :visible-date="visibleDate"
              :event="event"
              @edit="edit(event)"
            />
          </div>
          <div
            v-else
            class="text-body-2 text-rui-text-secondary -mt-2"
          >
            {{ t('calendar.no_events') }}
          </div>
        </RuiCard>
        <RuiCard class="[&>div:last-child]:!pt-2">
          <template #header>
            {{ t('calendar.upcoming_events') }}
          </template>
          <CalendarUpcomingEventList
            v-if="upcomingEvents.length > 0"
            v-model:selected-date="selectedDate"
            :events="upcomingEvents"
            :visible-date="visibleDate"
            @edit="edit($event)"
          />
          <div
            v-else
            class="text-body-2 text-rui-text-secondary -mt-2"
          >
            {{ t('calendar.no_events') }}
          </div>
        </RuiCard>
      </div>
    </div>
  </TablePageLayout>
</template>

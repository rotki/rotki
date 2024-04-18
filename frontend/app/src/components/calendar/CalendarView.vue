<script setup lang="ts">
import dayjs, { type Dayjs } from 'dayjs';
import { RouterAccountsSchema } from '@/types/route';
import { isBlockchain } from '@/types/blockchain/chains';
import CalendarGrid from '@/components/calendar/CalendarGrid.vue';
import CalendarNavigator from '@/components/calendar/CalendarNavigator.vue';
import type { CalendarEvent, CalendarEventRequestPayload } from '@/types/history/calendar';
import type { Collection } from '@/types/collection';
import type { AddressData, BlockchainAccount } from '@/types/blockchain/accounts';
import type { Writeable } from '@/types';

const { t } = useI18n();

const selectedDate: Ref<Dayjs> = ref(dayjs());

const today: Ref<Dayjs> = ref(dayjs());
const range = ref<[number, number]>([0, 0]);

const { fetchCalendarEvents, deleteCalendarEvent } = useCalendarApi();
const accounts = ref<BlockchainAccount<AddressData>[]>([]);

const extraParams = computed(() => {
  const rangeVal = get(range);
  return {
    accounts: get(accounts).map(
      account => `${getAccountAddress(account)}#${account.chain}`,
    ),
    fromTimestamp: rangeVal[0].toString(),
    toTimestamp: rangeVal[1].toString(),
  };
});

const { getAccountByAddress } = useBlockchainStore();

const {
  state: events,
  isLoading,
  fetchData,
  editableItem,
} = usePaginationFilters<
  CalendarEvent,
  CalendarEventRequestPayload,
  CalendarEvent,
  Collection<CalendarEvent>
>(
  null,
  false,
  useEmptyFilter,
  fetchCalendarEvents,
  {
    onUpdateFilters(query) {
      const parsedAccounts = RouterAccountsSchema.parse(query);
      const accountsParsed = parsedAccounts.accounts;
      if (!accountsParsed || accountsParsed.length === 0)
        set(accounts, []);
      else
        set(accounts, accountsParsed.map(({ address, chain }) => getAccountByAddress(address, chain)));
    },
    defaultSortBy: {
      key: ['timestamp'],
      ascending: [true],
    },
    extraParams,
    customPageParams: computed<Partial<CalendarEventRequestPayload>>(() => {
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
  },
);

onMounted(() => {
  fetchData();
});

const eventsWithDate = computed(() => get(events).data.map(item => ({
  ...item,
  date: dayjs(item.timestamp * 1000).format('YYYY-MM-DD'),
})));

function setSelectedDate(day: Dayjs) {
  set(selectedDate, day);
}

function setToday() {
  const now = dayjs();
  set(today, now);
  setSelectedDate(now);
}

const { setOpenDialog, setPostSubmitFunc } = useCalendarEventForm();

function add() {
  set(editableItem, null);
  setOpenDialog(true);
}

function edit(event: CalendarEvent) {
  set(editableItem, event);
  setOpenDialog(true);
}

const { show } = useConfirmStore();
const { setMessage } = useMessageStore();

async function deleteClicked() {
  const item = get(editableItem);
  if (item) {
    try {
      await deleteCalendarEvent(item.identifier);
      await fetchData();
      setOpenDialog(false);
      set(editableItem, null);
    }
    catch (error: any) {
      setMessage({
        title: t('calendar.delete_event'),
        description: t('calendar.delete_error.message', { message: error.message }),
        success: false,
      });
    }
  }
}

function deleteEvent() {
  show({
    title: t('calendar.delete_event'),
    message: t('calendar.dialog.delete.message'),
  }, deleteClicked);
}

setPostSubmitFunc(fetchData);

const selectedDateEvents = computed(() => get(eventsWithDate).filter(item => item.date === get(selectedDate).format('YYYY-MM-DD')));
</script>

<template>
  <TablePageLayout
    :title="[
      t('navigation_menu.calendar'),
    ]"
  >
    <template #buttons>
      <RuiButton
        color="primary"
        @click="add()"
      >
        <template #prepend>
          <RuiIcon name="add-line" />
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
              multiple
              dense
              outlined
            />
          </template>
          <div class="flex gap-4">
            <CalendarNavigator
              v-model="selectedDate"
            />
            <RuiButton
              color="primary"
              variant="outlined"
              :disabled="selectedDate.isSame(today, 'day')"
              @click="setToday()"
            >
              {{ t('calendar.today') }}
            </RuiButton>
          </div>
        </HistoryTableActions>
        <CalendarGrid
          :today="today"
          :selected-date="selectedDate"
          :events-with-date="eventsWithDate"
          @update:selected-date="setSelectedDate($event)"
          @update:range="range = $event"
          @edit="edit($event)"
          @add="add()"
        />

        <CalendarFormDialog
          :editable-item="editableItem"
          :loading="isLoading"
          :selected-date="selectedDate"
          @delete="deleteEvent()"
        />
      </RuiCard>
      <RuiCard class="h-auto">
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
          class="flex flex-col gap-4 pb-2"
        >
          <CalendarEventList
            v-for="event in selectedDateEvents"
            :key="event.identifier"
            :event="event"
            @edit="edit(event)"
          />
        </div>
        <div
          v-else
          class="text-body-2 pb-2"
        >
          {{ t('calendar.no_events') }}
        </div>
      </RuiCard>
    </div>
  </TablePageLayout>
</template>

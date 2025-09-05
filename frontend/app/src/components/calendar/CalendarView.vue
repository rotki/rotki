<script setup lang="ts">
import type { AddressData, BlockchainAccount } from '@/types/blockchain/accounts';
import dayjs from 'dayjs';
import CalendarDateNavigator from '@/components/calendar/CalendarDateNavigator.vue';
import CalendarFormDialog from '@/components/calendar/CalendarFormDialog.vue';
import CalendarGrid from '@/components/calendar/CalendarGrid.vue';
import CalendarMonthNavigator from '@/components/calendar/CalendarMonthNavigator.vue';
import CalendarSelectedEventsPanel from '@/components/calendar/CalendarSelectedEventsPanel.vue';
import CalendarSettingsMenu from '@/components/calendar/CalendarSettingsMenu.vue';
import CalendarUpcomingEventsPanel from '@/components/calendar/CalendarUpcomingEventsPanel.vue';
import BlockchainAccountSelector from '@/components/helper/BlockchainAccountSelector.vue';
import HistoryTableActions from '@/components/history/HistoryTableActions.vue';
import TablePageLayout from '@/components/layout/TablePageLayout.vue';
import { useCalendarData } from '@/composables/calendar/use-calendar-data';
import { useCalendarDateManagement } from '@/composables/calendar/use-calendar-date-management';
import { useCalendarOperations } from '@/composables/calendar/use-calendar-operations';

const { t } = useI18n({ useScope: 'global' });

// State
const accounts = ref<BlockchainAccount<AddressData>[]>([]);

// Use composables
const {
  dateFormat,
  eventsWithDate,
  fetchData,
  initializePagination,
  isLoading,
  range,
  setToday: setTodayData,
  today,
  upcomingEvents,
} = useCalendarData(accounts);

const { selectedDate, selectedDateEvents, setSelectedDate, visibleDate } = useCalendarDateManagement(eventsWithDate, dateFormat);

const { add, deleteEvent, edit, editMode, modelValue } = useCalendarOperations(selectedDate, fetchData);

function setToday(): void {
  const now = setTodayData();
  setSelectedDate(now);
}

const route = useRoute();
const router = useRouter();

onMounted(async () => {
  initializePagination();

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
          @add="add($event)"
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
        <CalendarSelectedEventsPanel
          v-model:selected-date="selectedDate"
          :selected-date-events="selectedDateEvents"
          :today="today"
          :visible-date="visibleDate"
          @edit="edit($event)"
        />
        <CalendarUpcomingEventsPanel
          v-model:selected-date="selectedDate"
          :upcoming-events="upcomingEvents"
          :visible-date="visibleDate"
          @edit="edit($event)"
        />
      </div>
    </div>
  </TablePageLayout>
</template>

<script setup lang="ts">
import type { AddressData, BlockchainAccount } from '@/modules/accounts/blockchain-accounts';
import dayjs from 'dayjs';
import BlockchainAccountSelector from '@/modules/accounts/BlockchainAccountSelector.vue';
import CalendarDateNavigator from '@/modules/calendar/CalendarDateNavigator.vue';
import CalendarFormDialog from '@/modules/calendar/CalendarFormDialog.vue';
import CalendarGrid from '@/modules/calendar/CalendarGrid.vue';
import CalendarMonthNavigator from '@/modules/calendar/CalendarMonthNavigator.vue';
import CalendarSelectedEventsPanel from '@/modules/calendar/CalendarSelectedEventsPanel.vue';
import CalendarSettingsMenu from '@/modules/calendar/CalendarSettingsMenu.vue';
import CalendarUpcomingEventsPanel from '@/modules/calendar/CalendarUpcomingEventsPanel.vue';
import { useCalendarData } from '@/modules/calendar/use-calendar-data';
import { useCalendarDateManagement } from '@/modules/calendar/use-calendar-date-management';
import { useCalendarOperations } from '@/modules/calendar/use-calendar-operations';
import HistoryTableActions from '@/modules/history/HistoryTableActions.vue';
import TablePageLayout from '@/modules/shell/layout/TablePageLayout.vue';

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
  modelRange,
  setToday: setTodayData,
  today,
  upcomingEvents,
} = useCalendarData(accounts);

const { modelSelectedDate, selectedDateEvents, setSelectedDate, modelVisibleDate } = useCalendarDateManagement(eventsWithDate, dateFormat);

const { add, deleteEvent, edit, editMode, modelValue } = useCalendarOperations(modelSelectedDate, fetchData);

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
      set(modelSelectedDate, date);

    await router.replace({ query: {} });
  }
});
</script>

<template>
  <TablePageLayout :title="[t('navigation_menu.calendar')]">
    <template #buttons>
      <RuiButton
        color="primary"
        size="lg"
        data-testid="calendar-add-event"
        @click="add()"
      >
        <template #prepend>
          <RuiIcon name="lu-plus" />
        </template>
        {{ t('calendar.add_event') }}
      </RuiButton>
      <CalendarSettingsMenu />
    </template>

    <div class="grid items-start grid-cols-[minmax(0,1fr)_14rem] gap-4">
      <RuiCard class="h-auto">
        <HistoryTableActions>
          <template #filter>
            <BlockchainAccountSelector
              v-model="accounts"
              class="md:w-[24rem]"
              :source="{ multichain: true }"
              :field="{ dense: true }"
            />
          </template>
          <div class="flex gap-4">
            <CalendarMonthNavigator v-model="modelVisibleDate" />
            <CalendarDateNavigator
              v-model="modelSelectedDate"
              :visible-date="modelVisibleDate"
              :today="today"
              @set-today="setToday()"
            />
          </div>
        </HistoryTableActions>
        <CalendarGrid
          :today="today"
          :selected-date="modelSelectedDate"
          :visible-date="modelVisibleDate"
          :events-with-date="eventsWithDate"
          @update:selected-date="setSelectedDate($event)"
          @update:range="modelRange = $event"
          @edit="edit($event)"
          @add="add($event)"
        />

        <CalendarFormDialog
          v-model="modelValue"
          :loading="isLoading"
          :selected-date="modelSelectedDate"
          :edit-mode="editMode"
          @delete="deleteEvent()"
          @refresh="fetchData()"
        />
      </RuiCard>
      <div class="flex flex-col gap-4 h-auto">
        <CalendarSelectedEventsPanel
          v-model:selected-date="modelSelectedDate"
          :selected-date-events="selectedDateEvents"
          :today="today"
          :visible-date="modelVisibleDate"
          @edit="edit($event)"
        />
        <CalendarUpcomingEventsPanel
          v-model:selected-date="modelSelectedDate"
          :upcoming-events="upcomingEvents"
          :visible-date="modelVisibleDate"
          @edit="edit($event)"
        />
      </div>
    </div>
  </TablePageLayout>
</template>

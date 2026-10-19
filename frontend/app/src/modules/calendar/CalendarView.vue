<script setup lang="ts">
import type { AddressAccount } from '@/modules/accounts/blockchain-accounts';
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
import TableFrame from '@/modules/core/table/TableFrame.vue';
import TablePageLayout from '@/modules/shell/layout/TablePageLayout.vue';

const { t } = useI18n({ useScope: 'global' });

const accounts = ref<AddressAccount[]>([]);

const {
  dateFormat,
  error,
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

    <div class="grid items-start gap-4 xl:grid-cols-[minmax(0,1fr)_16rem]">
      <TableFrame>
        <template #toolbar>
          <CalendarDateNavigator
            v-model="modelSelectedDate"
            :visible-date="modelVisibleDate"
            :today="today"
            @set-today="setToday()"
          />
          <CalendarMonthNavigator v-model="modelVisibleDate" />
          <BlockchainAccountSelector
            v-model="accounts"
            class="w-full md:ml-auto md:w-72"
            label-placement="hidden"
            :menu-options="{ classNames: { menu: 'w-72' } }"
            :placeholder="t('calendar.all_addresses')"
            :source="{ multichain: true }"
            :field="{ dense: true, label: t('calendar.all_addresses') }"
          />
        </template>
        <RuiAlert
          v-if="error"
          type="error"
          class="m-3"
          :title="t('data_table.fetch_failed')"
          data-testid="calendar-fetch-error"
        >
          <div class="flex flex-col items-start gap-2">
            <span>{{ error.message }}</span>
            <RuiButton
              size="sm"
              color="error"
              variant="outlined"
              data-testid="calendar-retry"
              @click="fetchData()"
            >
              {{ t('common.actions.retry') }}
            </RuiButton>
          </div>
        </RuiAlert>
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
      </TableFrame>
      <div class="grid items-start gap-4 md:grid-cols-2 xl:flex xl:flex-col">
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

    <CalendarFormDialog
      v-model="modelValue"
      :loading="isLoading"
      :edit-mode="editMode"
      @delete="deleteEvent()"
      @refresh="fetchData()"
    />
  </TablePageLayout>
</template>

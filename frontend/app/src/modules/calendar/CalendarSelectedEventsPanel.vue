<script setup lang="ts">
import type { Dayjs } from 'dayjs';
import type { CalendarEvent } from '@/modules/calendar/types';
import CalendarEventList from '@/modules/calendar/CalendarEventList.vue';
import DateDisplay from '@/modules/shell/components/display/DateDisplay.vue';

const selectedDate = defineModel<Dayjs>('selectedDate', { required: true });

defineProps<{
  selectedDateEvents: CalendarEvent[];
  today: Dayjs;
  visibleDate: Dayjs;
}>();

const emit = defineEmits<{
  edit: [event: CalendarEvent];
}>();

const { t } = useI18n({ useScope: 'global' });

function edit(event: CalendarEvent): void {
  emit('edit', event);
}
</script>

<template>
  <section
    class="flex flex-col gap-2 rounded-rui-card border border-rui-divider bg-rui-surface p-4"
    data-testid="calendar-selected-list"
  >
    <div class="text-sm font-semibold text-rui-text">
      <template v-if="today.isSame(selectedDate, 'day')">
        {{ t('calendar.today_events') }}
      </template>
      <template v-else>
        <DateDisplay
          :timestamp="selectedDate.unix()"
          no-time
          hide-tooltip
        />
        {{ t('common.events') }}
      </template>
    </div>
    <div
      v-if="selectedDateEvents.length > 0"
      class="flex flex-col gap-1"
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
      class="text-sm text-rui-text-secondary"
    >
      {{ t('calendar.no_events') }}
    </div>
  </section>
</template>

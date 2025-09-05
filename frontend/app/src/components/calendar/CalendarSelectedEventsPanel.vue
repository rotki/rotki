<script setup lang="ts">
import type { Dayjs } from 'dayjs';
import type { CalendarEvent } from '@/types/history/calendar';
import CalendarEventList from '@/components/calendar/CalendarEventList.vue';
import DateDisplay from '@/components/display/DateDisplay.vue';

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
</template>

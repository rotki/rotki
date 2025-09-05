<script setup lang="ts">
import type { Dayjs } from 'dayjs';
import type { CalendarEvent } from '@/types/history/calendar';
import CalendarUpcomingEventList from '@/components/calendar/CalendarUpcomingEventList.vue';

const selectedDate = defineModel<Dayjs>('selectedDate', { required: true });

defineProps<{
  upcomingEvents: CalendarEvent[];
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
</template>

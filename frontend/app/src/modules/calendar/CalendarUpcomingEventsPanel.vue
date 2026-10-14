<script setup lang="ts">
import type { Dayjs } from 'dayjs';
import type { CalendarEvent } from '@/modules/calendar/types';
import CalendarUpcomingEventList from '@/modules/calendar/CalendarUpcomingEventList.vue';

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
  <section
    class="flex flex-col gap-3 rounded-rui-card border border-rui-divider bg-rui-surface p-4"
    data-testid="calendar-upcoming-list"
  >
    <div class="text-sm font-semibold text-rui-text">
      {{ t('calendar.upcoming_events') }}
    </div>
    <CalendarUpcomingEventList
      v-if="upcomingEvents.length > 0"
      v-model:selected-date="selectedDate"
      :events="upcomingEvents"
      :visible-date="visibleDate"
      @edit="edit($event)"
    />
    <div
      v-else
      class="text-sm text-rui-text-secondary"
    >
      {{ t('calendar.no_events') }}
    </div>
  </section>
</template>

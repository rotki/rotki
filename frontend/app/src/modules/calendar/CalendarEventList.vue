<script setup lang="ts">
import type { CalendarEvent } from '@/modules/calendar/types';
import dayjs, { type Dayjs } from 'dayjs';

const selectedDate = defineModel<Dayjs>('selectedDate', { required: true });

const { event, visibleDate } = defineProps<{
  visibleDate: Dayjs;
  event: CalendarEvent;
}>();

const emit = defineEmits<{
  edit: [event: CalendarEvent];
}>();

function edit(calendarEvent: CalendarEvent) {
  emit('edit', calendarEvent);
}

const time = computed<string>(() => dayjs(event.timestamp * 1000).format('HH:mm'));

const MAX_LENGTH = 70;

const showTooltip = computed<boolean>(() => {
  const desc = event.description;
  return desc !== undefined && desc.length > MAX_LENGTH;
});

const description = computed<string>(() => {
  const desc = event.description;
  if (desc === undefined) {
    return '';
  }
  if (!get(showTooltip))
    return desc;

  return `${desc.slice(0, MAX_LENGTH)}...`;
});

const { t } = useI18n({ useScope: 'global' });

function onEventClicked(calendarEvent: CalendarEvent) {
  if (!get(selectedDate).isSame(visibleDate, 'month')) {
    set(selectedDate, dayjs(calendarEvent.timestamp * 1000));
  }

  edit(calendarEvent);
}
</script>

<template>
  <div class="flex items-center gap-4">
    <div
      class="min-w-5 min-h-5 rounded-full"
      :style="{
        backgroundColor: `#${event.color}`,
      }"
    />
    <div>
      <div class="text-body-2 font-medium">
        {{ event.name }}
      </div>
      <RuiTooltip
        v-if="event.description"
        :popper="{ placement: 'left' }"
        :disabled="!showTooltip"
        :open-delay="400"
        tooltip-class="max-w-[20rem] whitespace-break-spaces"
      >
        <template #activator>
          <div class="text-body-2 text-rui-text-secondary">
            {{ description }}
          </div>
        </template>
        <span>{{ event.description }}</span>
      </RuiTooltip>
      <div class="text-caption">
        {{ time }}
      </div>
      <div>
        <RuiButton
          color="primary"
          variant="text"
          size="sm"
          class="-ml-1"
          @click="onEventClicked(event)"
        >
          {{ t('calendar.view_details') }}
        </RuiButton>
      </div>
    </div>
  </div>
</template>

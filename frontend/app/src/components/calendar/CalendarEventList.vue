<script setup lang="ts">
import type { CalendarEvent } from '@/types/history/calendar';
import dayjs, { type Dayjs } from 'dayjs';

const selectedDate = defineModel<Dayjs>('selectedDate', { required: true });

const props = defineProps<{
  visibleDate: Dayjs;
  event: CalendarEvent;
}>();

const emit = defineEmits<{
  (e: 'edit', event: CalendarEvent): void;
}>();

function edit(event: CalendarEvent) {
  emit('edit', event);
}

const { event } = toRefs(props);

const time = computed(() => dayjs(get(event).timestamp * 1000).format('HH:mm'));

const MAX_LENGTH = 70;

const showTooltip = computed<boolean>(() => {
  const description = get(event).description;
  return description !== undefined && description.length > MAX_LENGTH;
});

const description = computed<string>(() => {
  const description = get(event).description;
  if (description === undefined) {
    return '';
  }
  if (!get(showTooltip))
    return description;

  return `${description.slice(0, MAX_LENGTH)}...`;
});

const { t } = useI18n({ useScope: 'global' });

function onEventClicked(event: CalendarEvent) {
  if (!get(selectedDate).isSame(props.visibleDate, 'month')) {
    set(selectedDate, dayjs(event.timestamp * 1000));
  }

  edit(event);
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

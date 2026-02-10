<script setup lang="ts">
import { toSentenceCase } from '@rotki/common';
import LocationIcon from '@/components/history/LocationIcon.vue';
import { type LocationProgress, LocationStatus } from '../types';

const props = withDefaults(defineProps<{
  location: LocationProgress;
  compact?: boolean;
}>(), {
  compact: false,
});

const { t } = useI18n({ useScope: 'global' });

const isComplete = computed<boolean>(() => props.location.status === LocationStatus.COMPLETE);
const isQuerying = computed<boolean>(() => props.location.status === LocationStatus.QUERYING);

const statusIcon = computed<string>(() => {
  if (get(isComplete))
    return 'lu-check';
  if (get(isQuerying))
    return 'lu-loader-circle';
  return 'lu-circle';
});

const statusColor = computed<string>(() => {
  if (get(isComplete))
    return 'text-rui-success';
  if (get(isQuerying))
    return 'text-rui-primary';
  return 'text-rui-text-disabled';
});

const statusText = computed<string>(() => {
  if (get(isComplete))
    return t('sync_progress.status.complete');

  if (get(isQuerying)) {
    if (props.location.eventType) {
      const eventType = props.location.eventType;
      const type = eventType === 'history_query'
        ? t('common.events')
        : toSentenceCase(props.location.eventType);
      return t('sync_progress.status.querying_event_type', { type });
    }
    return t('sync_progress.status.querying');
  }

  return t('sync_progress.status.pending');
});

const statusBorderColor = computed<string>(() => {
  if (get(isComplete))
    return 'border-l-rui-success';
  if (get(isQuerying))
    return 'border-l-rui-primary';
  return 'border-l-rui-grey-400 dark:border-l-rui-grey-600';
});
</script>

<template>
  <div
    class="flex items-center gap-3 px-2 rounded-r border-l-2 hover:bg-rui-grey-100 dark:hover:bg-rui-grey-700 transition-colors"
    :class="[statusBorderColor, compact ? 'py-1' : 'py-2', { 'animate-pulse bg-rui-primary/5': isQuerying }]"
  >
    <LocationIcon
      :item="location.location"
      icon
      :size="compact ? '16px' : '20px'"
    />

    <span
      class="font-medium flex-1 text-rui-text"
      :class="compact ? 'text-xs' : 'text-sm'"
    >
      {{ location.name }}
    </span>

    <span
      class="text-rui-text-secondary whitespace-nowrap"
      :class="compact ? 'text-[10px]' : 'text-xs'"
    >
      {{ statusText }}
    </span>

    <RuiIcon
      :name="statusIcon"
      :class="[statusColor, { 'animate-spin': isQuerying }]"
      :size="compact ? 12 : 16"
    />
  </div>
</template>

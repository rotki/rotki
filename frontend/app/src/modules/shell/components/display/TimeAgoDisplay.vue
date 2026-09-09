<script setup lang="ts">
import DateDisplay from '@/modules/shell/components/display/DateDisplay.vue';

const { milliseconds = false, timestamp } = defineProps<{
  /** Seconds since the epoch, or milliseconds when `milliseconds` is set. */
  timestamp: number;
  milliseconds?: boolean;
}>();

const timeAgo = useTimeAgo(() => milliseconds ? timestamp : timestamp * 1000);
</script>

<template>
  <RuiTooltip :open-delay="300">
    <template #activator>
      <span class="whitespace-nowrap">{{ timeAgo }}</span>
    </template>
    <DateDisplay
      :timestamp="timestamp"
      :milliseconds="milliseconds"
    />
  </RuiTooltip>
</template>

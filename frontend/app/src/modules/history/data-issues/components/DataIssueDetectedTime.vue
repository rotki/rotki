<script setup lang="ts">
import DateDisplay from '@/modules/shell/components/display/DateDisplay.vue';

const { timestamp } = defineProps<{
  timestamp: number;
}>();

const timeAgo = useTimeAgo(() => timestamp * 1000);
</script>

<template>
  <RuiTooltip :open-delay="300">
    <template #activator>
      <span class="whitespace-nowrap">{{ timeAgo }}</span>
    </template>
    <DateDisplay :timestamp="timestamp" />
  </RuiTooltip>
</template>

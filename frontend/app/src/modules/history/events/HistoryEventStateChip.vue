<script setup lang="ts">
import type { HistoryEventState } from '@/modules/history/events/schemas';
import { useHistoryEventStateMapping } from '@/modules/history/events/mapping/use-history-event-state-mapping';

const { state } = defineProps<{
  state: HistoryEventState;
}>();

const { stateConfigs } = useHistoryEventStateMapping();

const config = computed(() => stateConfigs[state]);
</script>

<template>
  <RuiTooltip :options="{ autoUpdate: { resize: false, scroll: false }, placement: 'top' }">
    <template #activator>
      <RuiChip
        size="sm"
        :color="config.color"
        class="!p-0.5"
      >
        <RuiIcon
          :name="config.icon"
          size="14"
        />
      </RuiChip>
    </template>
    {{ config.label }}
  </RuiTooltip>
</template>

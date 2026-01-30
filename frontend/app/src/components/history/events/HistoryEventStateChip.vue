<script setup lang="ts">
import type { HistoryEventState } from '@/types/history/events/schemas';
import { useHistoryEventStateMapping } from '@/composables/history/events/mapping/state';

const props = defineProps<{
  state: HistoryEventState;
}>();

const { stateConfigs } = useHistoryEventStateMapping();

const config = computed(() => stateConfigs[props.state]);
</script>

<template>
  <RuiChip
    size="sm"
    :color="config.color"
    class="px-1"
  >
    <div class="flex items-center gap-1 text-caption font-bold !text-xs">
      <RuiIcon
        :name="config.icon"
        size="14"
      />
      {{ config.label }}
    </div>
  </RuiChip>
</template>

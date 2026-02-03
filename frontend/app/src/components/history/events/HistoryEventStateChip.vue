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
  <RuiTooltip :popper="{ placement: 'top', scroll: false, resize: false }">
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

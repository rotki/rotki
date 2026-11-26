<script setup lang="ts">
import { RuiButton, RuiIcon, RuiTooltip } from '@rotki/ui-library';

const { tooltip, disabled = false } = defineProps<{
  tooltip: string;
  disabled?: boolean;
}>();

const emit = defineEmits<{
  reconnect: [];
}>();
</script>

<template>
  <RuiTooltip :open-delay="400">
    <template #activator>
      <RuiButton
        :disabled="disabled"
        icon
        color="primary"
        variant="text"
        size="sm"
        @click="emit('reconnect')"
      >
        <RuiIcon
          name="lu-rotate-cw"
          size="16"
        />
      </RuiButton>
    </template>
    {{ tooltip }}
  </RuiTooltip>
</template>

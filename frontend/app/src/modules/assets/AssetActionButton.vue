<script setup lang="ts">
import type { RuiIcons } from '@rotki/ui-library';

const { color, dataTestid, icon, tooltip } = defineProps<{
  icon: RuiIcons;
  color: 'primary' | 'warning' | 'error';
  tooltip: string;
  dataTestid?: string;
}>();

const emit = defineEmits<{
  click: [];
}>();
</script>

<template>
  <RuiTooltip
    :open-delay="200"
    :options="{ placement: 'top' }"
  >
    <template #activator>
      <RuiButton
        variant="text"
        :color="color"
        class="!py-0.5"
        size="sm"
        :data-testid="dataTestid"
        @click="emit('click')"
      >
        <template #append>
          <RuiIcon
            :name="icon"
            size="18"
          />
        </template>
      </RuiButton>
    </template>
    {{ tooltip }}
  </RuiTooltip>
</template>

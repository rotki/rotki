<script setup lang="ts">
import type { ContextColorsType, RuiButton, RuiIcons } from '@rotki/ui-library';
import type { ForwardedProps } from '@/modules/core/common/forwarded-props';

import { useTableSelectionCollapsed } from '@/modules/core/table/table-selection-collapse';

interface Props {
  icon: RuiIcons;
  color?: ContextColorsType;
  disabled?: boolean;
  loading?: boolean;
}

const { color, disabled = false, loading = false } = defineProps<Props & /* @vue-ignore */ ForwardedProps<typeof RuiButton, Props, 'click'>>();

const emit = defineEmits<{
  click: [];
}>();

defineSlots<{
  default: () => any;
}>();

const collapsed = useTableSelectionCollapsed();
</script>

<template>
  <RuiButton
    v-if="collapsed"
    variant="list"
    :color="color"
    :disabled="disabled || loading"
    @click="emit('click')"
  >
    <template #prepend>
      <RuiIcon :name="icon" />
    </template>
    <slot />
  </RuiButton>
  <RuiButton
    v-else
    size="sm"
    variant="outlined"
    :color="color"
    :disabled="disabled"
    :loading="loading"
    @click="emit('click')"
  >
    <template #prepend>
      <RuiIcon
        :name="icon"
        size="16"
      />
    </template>
    <slot />
  </RuiButton>
</template>

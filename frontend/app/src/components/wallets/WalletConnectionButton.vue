<script setup lang="ts">
import type { ContextColorsType } from '@rotki/ui-library';

interface Props {
  size?: 'sm' | 'lg';
  variant?: 'default' | 'outlined' | 'text';
  color?: ContextColorsType;
  fullWidth?: boolean;
  disabled?: boolean;
  loading?: boolean;
  connected: boolean;
}

const props = withDefaults(defineProps<Props>(), {
  color: 'primary',
  disabled: false,
  fullWidth: false,
  loading: false,
  size: undefined,
  variant: 'default',
});

const emit = defineEmits<{
  click: [];
}>();

const { t } = useI18n({ useScope: 'global' });

function getButtonText(): string {
  if (props.connected) {
    return t('trade.actions.disconnect');
  }
  return t('trade.actions.connect_wallet');
}
</script>

<template>
  <div>
    <RuiButton
      :size="size"
      :variant="variant"
      :color="color"
      :class="{ '!w-full': fullWidth }"
      :loading="loading"
      :disabled="disabled"
      @click="emit('click')"
    >
      {{ getButtonText() }}
    </RuiButton>
  </div>
</template>

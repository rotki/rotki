<script setup lang="ts">
import type { ContextColorsType } from '@rotki/ui-library';
import { useWalletStore } from '@/modules/onchain/use-wallet-store';

interface Props {
  size?: 'sm' | 'lg';
  variant?: 'default' | 'outlined' | 'text';
  color?: ContextColorsType;
  fullWidth?: boolean;
  disabled?: boolean;
  loading?: boolean;
}

withDefaults(defineProps<Props>(), {
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

const { connected, connectedAddress } = storeToRefs(useWalletStore());

function getButtonText(): string {
  if (get(connected)) {
    const address = get(connectedAddress);
    return address ? `${address.slice(0, 6)}...${address.slice(-4)}` : t('trade.actions.disconnect');
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

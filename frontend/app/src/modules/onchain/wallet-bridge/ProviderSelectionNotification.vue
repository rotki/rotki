<script setup lang="ts">
import { useUnifiedProviders } from '../wallet-providers/use-unified-providers';

const { t } = useI18n({ useScope: 'global' });

const { availableProviders, hasSelectedProvider } = useUnifiedProviders();

const shouldShowNotification = computed<boolean>(() => {
  const providers = get(availableProviders);
  const hasSelected = get(hasSelectedProvider);

  // Show notification when multiple providers available but none selected
  return providers.length > 1 && !hasSelected;
});

const providerCount = computed<number>(() => get(availableProviders).length);
</script>

<template>
  <div
    v-if="shouldShowNotification"
    class="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-50"
  >
    <RuiAlert
      type="info"
      variant="default"
      class="max-w-md"
    >
      <div class="flex-1 min-w-0">
        <p class="text-lg text-rui-text font-medium mb-1">
          {{ t('trade.bridge.multiple_providers_detected') }}
        </p>
        <p class="text-md text-rui-text-secondary">
          {{ t('trade.bridge.multiple_providers_message', { count: providerCount }) }}
        </p>
      </div>
    </RuiAlert>
  </div>
</template>

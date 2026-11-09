<script setup lang="ts">
import { useUnifiedProviders } from '../providers/use-unified-providers';
import BridgeOverlay from './BridgeOverlay.vue';

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
  <BridgeOverlay
    v-if="shouldShowNotification"
    color="info"
    icon="lu-info"
    :title="t('trade.bridge.multiple_providers_detected')"
    :description="t('trade.bridge.multiple_providers_message', { count: providerCount })"
  />
</template>

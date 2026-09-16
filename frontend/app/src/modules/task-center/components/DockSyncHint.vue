<script setup lang="ts">
import { useExternalApiKeys } from '@/modules/settings/api-keys/external/use-external-api-keys';

const { t } = useI18n({ useScope: 'global' });

const { loading: apiKeysLoading, useApiKey } = useExternalApiKeys();
const etherscanKey = useApiKey('etherscan');

/**
 * Whether to offer the free Etherscan key tip, which only helps someone who has not set one. Gated
 * on the load as well as the key, since `useApiKey` reads `''` until the keys arrive and the tip
 * would otherwise flash for everyone who already has one.
 */
const showEtherscanHint = computed<boolean>(() => !get(apiKeysLoading) && !get(etherscanKey));
</script>

<template>
  <div
    class="text-xs leading-4 text-rui-text-secondary"
    data-testid="dock-sync-hint"
  >
    {{ t('task_dock.sync_hint.explanation') }}
    <template v-if="showEtherscanHint">
      {{ t('task_dock.sync_hint.etherscan') }}
      <RouterLink
        class="text-rui-primary font-medium"
        :to="{ name: '/api-keys/external/' }"
        data-testid="dock-sync-hint-etherscan"
      >
        {{ t('task_dock.sync_hint.add_key') }}
      </RouterLink>
    </template>
  </div>
</template>

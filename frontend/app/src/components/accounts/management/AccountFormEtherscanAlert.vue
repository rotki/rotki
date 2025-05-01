<script setup lang="ts">
import { Routes } from '@/router/routes';

const { t } = useI18n();
</script>

<template>
  <RuiAlert
    type="warning"
    class="mb-4"
  >
    {{ t('external_services.etherscan.api_key_message') }}
    <RouterLink
      :to="{
        path: Routes.API_KEYS_EXTERNAL_SERVICES.toString(),
        query: { service: 'etherscan' },
      }"
    >
      <RuiButton
        color="primary"
        variant="text"
        size="sm"
        class="inline underline"
      >
        {{ t('notification_messages.missing_api_key.action') }}
      </RuiButton>
    </RouterLink>
  </RuiAlert>
</template>

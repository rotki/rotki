<script setup lang="ts">
import { Routes } from '@/router/routes';

const props = defineProps<{
  service: 'etherscan' | 'helius';
}>();

const { t } = useI18n({ useScope: 'global' });

const message = computed<string>(() => {
  if (props.service === 'etherscan')
    return t('external_services.etherscan.api_key_message');

  return t('external_services.helius.api_key_message');
});
</script>

<template>
  <RuiAlert
    type="warning"
    class="mb-8 -mt-2"
  >
    {{ message }}
    <RouterLink
      :to="{
        path: Routes.API_KEYS_EXTERNAL_SERVICES.toString(),
        query: { service },
      }"
    >
      <RuiButton
        color="primary"
        variant="text"
        size="sm"
        class="inline -my-1 ml-auto [&>span]:underline"
      >
        {{ t('notification_messages.missing_api_key.action') }}
      </RuiButton>
    </RouterLink>
  </RuiAlert>
</template>

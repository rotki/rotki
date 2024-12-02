<script setup lang="ts">
const { t } = useI18n();

const coinbaseApiKeyNameFormat = 'organizations/{org_id}/apiKeys/{key_id}';
const coinbasePrivateKeyFormat = '-----BEGIN EC PRIVATE KEY-----\\n{KEY}\\n-----END EC PRIVATE KEY-----\\n';

const apiKeyLabel = t('exchange_settings.inputs.api_key_name');
const apiKeyHint = `${t('exchange_settings.inputs.format')}: ${coinbaseApiKeyNameFormat}`;

const apiSecretLabel = t('exchange_settings.inputs.private_key');
const apiSecretHint = `${t('exchange_settings.inputs.format')}: ${coinbasePrivateKeyFormat}`;
</script>

<template>
  <slot
    name="apiKey"
    v-bind="{ label: apiKeyLabel, hint: apiKeyHint }"
  />
  <slot
    name="apiSecret"
    v-bind="{ label: apiSecretLabel, hint: apiSecretHint }"
  />
  <slot name="passphrase" />
</template>

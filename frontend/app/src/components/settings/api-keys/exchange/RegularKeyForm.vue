<script setup lang="ts">
const { t } = useI18n();

const apiKeyLabel = t('exchange_settings.inputs.api_key');
const apiKeyHint = '';

const apiSecretLabel = t('exchange_settings.inputs.api_secret');
const apiSecretHint = '';
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

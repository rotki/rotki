<script setup lang="ts">
const { t } = useI18n();

const apiKeyLabel = t('exchange_settings.inputs.access_key');
const apiKeyHint = '';

const apiSecretLabel = t('exchange_settings.inputs.signing_key');
const apiSecretHint = '';
</script>

<template>
  <slot
    name="apiKey"
    v-bind="{ label: apiKeyLabel, hint: apiKeyHint }"
  />
  <slot name="passphrase" />
  <slot
    name="apiSecret"
    v-bind="{ label: apiSecretLabel, hint: apiSecretHint }"
  />
</template>

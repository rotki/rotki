<script setup lang="ts">
const apiKey = defineModel<string>('apiKey', { required: true });
const apiSecret = defineModel<string>('apiSecret', { required: true });

const { apiKeyErrors = [], apiSecretErrors = [] } = defineProps<{
  apiKeyErrors?: string[];
  apiSecretErrors?: string[];
}>();

const emit = defineEmits<{
  blur: [field: 'apiKey' | 'apiSecret'];
}>();

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <div class="grid md:grid-cols-2 gap-x-4 gap-y-2">
    <RuiRevealableTextField
      v-model.trim="apiKey"
      data-testid="premium-api-key"
      color="primary"
      :error-messages="apiKeyErrors"
      :label="t('premium_settings.fields.api_key')"
      @blur="emit('blur', 'apiKey')"
    />
    <RuiRevealableTextField
      v-model.trim="apiSecret"
      data-testid="premium-api-secret"
      color="primary"
      :error-messages="apiSecretErrors"
      :label="t('premium_settings.fields.api_secret')"
      @blur="emit('blur', 'apiSecret')"
    />
  </div>
</template>

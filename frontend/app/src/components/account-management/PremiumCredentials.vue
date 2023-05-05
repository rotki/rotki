<script setup lang="ts">
import useVuelidate from '@vuelidate/core';
import { helpers, required } from '@vuelidate/validators';

const { t, tc } = useI18n();

const props = defineProps({
  loading: { required: true, type: Boolean },
  enabled: { required: true, type: Boolean },
  apiSecret: { required: true, type: String },
  apiKey: { required: true, type: String },
  syncDatabase: { required: true, type: Boolean }
});

const emit = defineEmits<{
  (e: 'update:api-key', apiKey: string): void;
  (e: 'update:api-secret', apiSecret: string): void;
  (e: 'update:sync-database', enabled: boolean): void;
  (e: 'update:valid', valid: boolean): void;
}>();
const { enabled, apiKey, apiSecret } = toRefs(props);

const updateApiKey = (apiKey: string | null) => {
  emit('update:api-key', apiKey?.trim() ?? '');
};

const updateApiSecret = (apiSecret: string | null) => {
  emit('update:api-secret', apiSecret?.trim() ?? '');
};

const updateSyncDatabase = (enabled: boolean | null) => {
  emit('update:sync-database', !!enabled);
};

const onApiKeyPaste = (_event: ClipboardEvent) => {
  const paste = trimOnPaste(_event);
  if (paste) {
    updateApiKey(paste);
  }
};

const onApiSecretPaste = (_event: ClipboardEvent) => {
  const paste = trimOnPaste(_event);
  if (paste) {
    updateApiSecret(paste);
  }
};

watch(enabled, enabled => {
  if (enabled) {
    return;
  }
  updateApiKey('');
  updateApiSecret('');
});

const rules = {
  apiKey: {
    required: helpers.withMessage(
      t('premium_credentials.validation.non_empty_key').toString(),
      required
    )
  },
  apiSecret: {
    required: helpers.withMessage(
      t('premium_credentials.validation.non_empty_secret').toString(),
      required
    )
  }
};

const v$ = useVuelidate(
  rules,
  {
    apiKey,
    apiSecret
  },
  {
    $autoDirty: true,
    $stopPropagation: true
  }
);

watch(v$, ({ $invalid }) => {
  emit('update:valid', !$invalid);
});
</script>

<template>
  <div>
    <div v-if="enabled">
      <v-switch
        :label="tc('premium_credentials.restore_synced_database')"
        :value="syncDatabase"
        @change="updateSyncDatabase($event)"
      />

      <revealable-input
        outlined
        :value="apiKey"
        :disabled="loading"
        class="premium-settings__fields__api-key"
        :error-messages="v$.apiKey.$errors.map(e => e.$message)"
        :label="tc('premium_credentials.label_api_key')"
        @input="updateApiKey($event)"
        @paste="onApiKeyPaste($event)"
      />
      <revealable-input
        outlined
        :value="apiSecret"
        :disabled="loading"
        class="premium-settings__fields__api-secret"
        prepend-icon="mdi-lock"
        :label="tc('premium_credentials.label_api_secret')"
        :error-messages="v$.apiSecret.$errors.map(e => e.$message)"
        @input="updateApiSecret($event)"
        @paste="onApiSecretPaste($event)"
      />
    </div>
  </div>
</template>

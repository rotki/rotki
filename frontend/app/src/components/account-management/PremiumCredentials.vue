<template>
  <div>
    <div v-if="enabled">
      <v-switch
        :label="tc('premium_credentials.restore_synced_database')"
        :value="syncDatabase"
        @change="updateSyncDatabase"
      />

      <revealable-input
        outlined
        :value="apiKey"
        :disabled="loading"
        class="premium-settings__fields__api-key"
        :rules="apiKeyRules"
        :label="tc('premium_credentials.label_api_key')"
        @input="updateApiKey"
        @paste="onApiKeyPaste"
      />
      <revealable-input
        outlined
        :value="apiSecret"
        :disabled="loading"
        class="premium-settings__fields__api-secret"
        prepend-icon="mdi-lock"
        :label="tc('premium_credentials.label_api_secret')"
        :rules="apiSecretRules"
        @input="updateApiSecret"
        @paste="onApiSecretPaste"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import RevealableInput from '@/components/inputs/RevealableInput.vue';
import { trimOnPaste } from '@/utils/event';

const { t, tc } = useI18n();
const apiKeyRules = [
  (v: string) =>
    !!v || t('premium_credentials.validation.non_empty_key').toString()
];
const apiSecretRules = [
  (v: string) =>
    !!v || t('premium_credentials.validation.non_empty_secret').toString()
];

const props = defineProps({
  loading: { required: true, type: Boolean },
  enabled: { required: true, type: Boolean },
  apiSecret: { required: true, type: String },
  apiKey: { required: true, type: String },
  syncDatabase: { required: true, type: Boolean }
});

const emit = defineEmits([
  'update:api-key',
  'update:api-secret',
  'update:sync-database'
]);
const { enabled } = toRefs(props);

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
</script>

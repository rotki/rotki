<template>
  <div>
    <div v-if="enabled">
      <v-switch
        :label="$t('premium_credentials.restore_synced_database')"
        :value="syncDatabase"
        @change="updateSyncDatabase"
      />

      <revealable-input
        outlined
        :value="apiKey"
        :disabled="loading"
        class="premium-settings__fields__api-key"
        :rules="apiKeyRules"
        :label="$t('premium_credentials.label_api_key')"
        @input="updateApiKey"
        @paste="onApiKeyPaste"
      />
      <revealable-input
        outlined
        :value="apiSecret"
        :disabled="loading"
        class="premium-settings__fields__api-secret"
        prepend-icon="mdi-lock"
        :label="$t('premium_credentials.label_api_secret')"
        :rules="apiSecretRules"
        @input="updateApiSecret"
        @paste="onApiSecretPaste"
      />
    </div>
  </div>
</template>

<script lang="ts">
import { defineComponent, ref, toRefs, watch } from '@vue/composition-api';
import { IVueI18n } from 'vue-i18n';
import RevealableInput from '@/components/inputs/RevealableInput.vue';
import i18n from '@/i18n';
import { trimOnPaste } from '@/utils/event';

const setupValidationRules = (i18n: IVueI18n) => {
  const apiKeyRules = [
    (v: string) =>
      !!v || i18n.t('premium_credentials.validation.non_empty_key').toString()
  ];
  const apiSecretRules = [
    (v: string) =>
      !!v ||
      i18n.t('premium_credentials.validation.non_empty_secret').toString()
  ];
  return { apiKeyRules, apiSecretRules };
};

const PremiumCredentials = defineComponent({
  name: 'PremiumCredentials',
  components: { RevealableInput },
  props: {
    loading: { required: true, type: Boolean },
    enabled: { required: true, type: Boolean },
    apiSecret: { required: true, type: String },
    apiKey: { required: true, type: String },
    syncDatabase: { required: true, type: Boolean }
  },
  emits: ['update:api-key', 'update:api-secret', 'update:sync-database'],
  setup(props, { emit }) {
    const { enabled } = toRefs(props);
    const showKey = ref(false);
    const showSecret = ref(false);

    const updateApiKey = (apiKey: string) => {
      emit('update:api-key', apiKey?.trim() ?? '');
    };

    const updateApiSecret = (apiSecret: string) => {
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

    return {
      updateApiKey,
      updateApiSecret,
      updateSyncDatabase,
      onApiKeyPaste,
      onApiSecretPaste,
      showKey,
      showSecret,
      ...setupValidationRules(i18n)
    };
  }
});
export default PremiumCredentials;
</script>

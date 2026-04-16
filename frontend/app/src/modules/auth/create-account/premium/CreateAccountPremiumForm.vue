<script setup lang="ts">
import type { PremiumSetup } from '@/modules/auth/login';
import useVuelidate from '@vuelidate/core';
import { helpers, requiredIf } from '@vuelidate/validators';
import { useRefPropVModel } from '@/modules/core/common/validation/model';
import { toMessages } from '@/modules/core/common/validation/validation';

const form = defineModel<PremiumSetup>('form', { required: true });
const valid = defineModel<boolean>('valid', { required: true });

const { loading, enabled } = defineProps<{
  loading: boolean;
  enabled: boolean;
}>();

const { t } = useI18n({ useScope: 'global' });

const apiKey = useRefPropVModel(form, 'apiKey');
const apiSecret = useRefPropVModel(form, 'apiSecret');
const syncDatabase = useRefPropVModel(form, 'syncDatabase');

watch(() => enabled, (enabled) => {
  if (!enabled)
    set(syncDatabase, false);
});

const rules = {
  apiKey: {
    required: helpers.withMessage(t('premium_credentials.validation.non_empty_key'), requiredIf(() => enabled)),
  },
  apiSecret: {
    required: helpers.withMessage(t('premium_credentials.validation.non_empty_secret'), requiredIf(() => enabled)),
  },
};

const v$ = useVuelidate(rules, form, {
  $autoDirty: true,
  $stopPropagation: true,
});

watchImmediate(v$, ({ $invalid }) => {
  set(valid, !$invalid);
});
</script>

<template>
  <div v-if="enabled">
    <div class="space-y-3">
      <RuiRevealableTextField
        v-model.trim="apiKey"
        dense
        variant="outlined"
        :disabled="loading"
        color="primary"
        :label="t('premium_credentials.label_api_key')"
        :error-messages="toMessages(v$.apiKey)"
      />
      <RuiRevealableTextField
        v-model.trim="apiSecret"
        dense
        variant="outlined"
        :disabled="loading"
        color="primary"
        :label="t('premium_credentials.label_api_secret')"
        :error-messages="toMessages(v$.apiSecret)"
      />
    </div>
    <RuiCheckbox
      v-model="syncDatabase"
      :disabled="loading"
      color="primary"
      hide-details
    >
      {{ t('premium_credentials.restore_synced_database') }}
    </RuiCheckbox>
  </div>
</template>

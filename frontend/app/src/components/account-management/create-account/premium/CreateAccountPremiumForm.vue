<script setup lang="ts">
import useVuelidate from '@vuelidate/core';
import { helpers, requiredIf } from '@vuelidate/validators';
import { toMessages } from '@/utils/validation';
import { type PremiumSetup } from '@/types/login';

const props = defineProps<{
  loading: boolean;
  enabled: boolean;
  form: PremiumSetup;
}>();

const emit = defineEmits<{
  (e: 'update:form', form: PremiumSetup): void;
  (e: 'update:valid', valid: boolean): void;
}>();

const { t } = useI18n();

const { enabled, form } = toRefs(props);

const apiKey = computed({
  get() {
    return get(form).apiKey;
  },
  set(value?: string) {
    input({ apiKey: value || '' });
  }
});

const apiSecret = computed({
  get() {
    return get(form).apiSecret;
  },
  set(value?: string) {
    input({ apiSecret: value || '' });
  }
});

const syncDatabase = computed({
  get() {
    return get(form).syncDatabase;
  },
  set(value: boolean) {
    input({ syncDatabase: value });
  }
});

watch(enabled, enabled => {
  if (!enabled) {
    set(syncDatabase, false);
  }
});

const rules = {
  apiKey: {
    required: helpers.withMessage(
      t('premium_credentials.validation.non_empty_key').toString(),
      requiredIf(enabled)
    )
  },
  apiSecret: {
    required: helpers.withMessage(
      t('premium_credentials.validation.non_empty_secret').toString(),
      requiredIf(enabled)
    )
  }
};

const v$ = useVuelidate(rules, form, {
  $autoDirty: true,
  $stopPropagation: true
});

watchImmediate(v$, ({ $invalid }) => {
  emit('update:valid', !$invalid);
});

const input = (newInput: Partial<PremiumSetup>) => {
  emit('update:form', {
    ...get(form),
    ...newInput
  });
};
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
        class="premium-settings__fields__api-key"
        :label="t('premium_credentials.label_api_key')"
        :error-messages="toMessages(v$.apiKey)"
      />
      <RuiRevealableTextField
        v-model.trim="apiSecret"
        dense
        variant="outlined"
        :disabled="loading"
        color="primary"
        class="premium-settings__fields__api-secret"
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

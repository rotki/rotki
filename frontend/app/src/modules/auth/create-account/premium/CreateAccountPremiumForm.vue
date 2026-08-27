<script setup lang="ts">
import type { ZodType } from 'zod';
import type { PremiumSetup } from '@/modules/auth/login';
import { premiumSetupSchema } from '@/modules/auth/create-account/premium/premium-setup-form';
import { syncStepValidity } from '@/modules/auth/create-account/step-validity';
import { useModelForm } from '@/modules/core/form/use-model-form';

const form = defineModel<PremiumSetup>('form', { required: true });
const valid = defineModel<boolean>('valid', { required: true });

const { loading, enabled } = defineProps<{
  loading: boolean;
  enabled: boolean;
}>();

const { t } = useI18n({ useScope: 'global' });

const schema = computed<ZodType>(() => premiumSetupSchema({
  apiKey: t('premium_credentials.validation.non_empty_key'),
  apiSecret: t('premium_credentials.validation.non_empty_secret'),
}, enabled));

const { errors, state, touch, valid: parses } = useModelForm<PremiumSetup>({
  model: form,
  schema,
});

syncStepValidity(parses, valid);
</script>

<template>
  <div v-if="enabled">
    <div class="space-y-3">
      <RuiRevealableTextField
        v-model.trim="state.apiKey"
        dense
        variant="outlined"
        :disabled="loading"
        color="primary"
        :label="t('premium_credentials.label_api_key')"
        :error-messages="errors('apiKey')"
        @update:model-value="touch('apiKey')"
      />
      <RuiRevealableTextField
        v-model.trim="state.apiSecret"
        dense
        variant="outlined"
        :disabled="loading"
        color="primary"
        :label="t('premium_credentials.label_api_secret')"
        :error-messages="errors('apiSecret')"
        @update:model-value="touch('apiSecret')"
      />
    </div>
  </div>
</template>

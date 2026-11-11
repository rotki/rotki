<script setup lang="ts">
import type { ZodType } from 'zod';
import type { PremiumSetup } from '@/modules/auth/login';
import { premiumSetupSchema } from '@/modules/auth/create-account/premium/premium-setup-form';
import { useFormErrorFocus } from '@/modules/core/common/use-form-error-focus';
import { useModelForm } from '@/modules/core/form/use-model-form';

const form = defineModel<PremiumSetup>({ required: true });

const { loading, optional = false } = defineProps<{
  loading: boolean;
  /** The credentials may be left out entirely, as on create: only a half-filled pair is an error. */
  optional?: boolean;
}>();

const { t } = useI18n({ useScope: 'global' });

const root = useTemplateRef<HTMLElement>('root');

const { focusFirstError } = useFormErrorFocus(root);

const required = computed<boolean>(() => !optional || get(form).apiKey !== '' || get(form).apiSecret !== '');

const schema = computed<ZodType>(() => premiumSetupSchema(optional
  ? {
      apiKey: t('create_account.premium.validation.optional_key'),
      apiSecret: t('create_account.premium.validation.optional_secret'),
    }
  : {
      apiKey: t('premium_credentials.validation.non_empty_key'),
      apiSecret: t('premium_credentials.validation.non_empty_secret'),
    }, get(required)));

const { errorCount, errors, state, touch, validate: revealErrors } = useModelForm<PremiumSetup>({
  model: form,
  schema,
});

/**
 * Reveals every error and moves focus to the first field holding one.
 *
 * @returns whether the step can be left
 */
async function validate(): Promise<boolean> {
  if (revealErrors())
    return true;
  await focusFirstError();
  return false;
}

defineExpose({ errorCount, validate });
</script>

<template>
  <div
    ref="root"
    class="flex flex-col gap-1"
  >
    <RuiRevealableTextField
      v-model.trim="state.apiKey"
      :disabled="loading"
      color="primary"
      data-testid="create-account-premium-api-key"
      :label="t('premium_credentials.label_api_key')"
      :error-messages="errors('apiKey')"
      @update:model-value="touch('apiKey')"
    />
    <RuiRevealableTextField
      v-model.trim="state.apiSecret"
      :disabled="loading"
      color="primary"
      data-testid="create-account-premium-api-secret"
      :label="t('premium_credentials.label_api_secret')"
      :error-messages="errors('apiSecret')"
      @update:model-value="touch('apiSecret')"
    />
  </div>
</template>

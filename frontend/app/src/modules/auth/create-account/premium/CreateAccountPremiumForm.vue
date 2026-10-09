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
  <!-- rows go 0fr ↔ 1fr so the fields slide open and shut instead of popping, and the leave
       transition keeps them mounted until they have collapsed -->
  <Transition
    enter-from-class="grid-rows-[0fr] opacity-0"
    enter-to-class="grid-rows-[1fr] opacity-100"
    enter-active-class="collapsing transition-[grid-template-rows,opacity] duration-200 ease-out motion-reduce:transition-none"
    leave-from-class="grid-rows-[1fr] opacity-100"
    leave-to-class="grid-rows-[0fr] opacity-0"
    leave-active-class="collapsing transition-[grid-template-rows,opacity] duration-150 ease-in motion-reduce:transition-none"
  >
    <div
      v-if="enabled"
      class="grid"
    >
      <!-- the spacing lives inside the collapsing row, so it opens with the fields rather than snapping
           in; the clip only applies mid-animation, so it never cuts the fields' focus ring -->
      <div class="min-h-0 in-[.collapsing]:overflow-hidden">
        <div class="space-y-3 pt-6">
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
    </div>
  </Transition>
</template>

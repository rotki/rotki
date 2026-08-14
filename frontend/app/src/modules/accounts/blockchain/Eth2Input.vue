<script setup lang="ts">
import type { ZodType } from 'zod';
import type { Eth2Validator } from '@/modules/balances/types/balances';
import type { ValidationErrors } from '@/modules/core/api/types/errors';
import {
  type Eth2ValidatorFormState,
  eth2ValidatorSchema,
  toFormState,
} from '@/modules/accounts/blockchain/eth2-validator-form';
import { useModelForm } from '@/modules/core/form/use-model-form';

const modelValue = defineModel<Eth2Validator>('validator', { required: true });

const errorMessages = defineModel<ValidationErrors>('errorMessages', { required: true });

defineProps<{
  disabled: boolean;
  editMode: boolean;
}>();

const { t } = useI18n({ useScope: 'global' });

const schema = computed<ZodType>(() => eth2ValidatorSchema({
  ownershipPercentage: t('eth2_input.ownership.validation'),
  required: t('eth2_input.validation.required'),
  validatorIndex: t('eth2_input.validator_index.validation'),
}));

/**
 * The payload is readonly and carries a field only once it has a value, so the form edits its own
 * copy and hands back a whole one.
 *
 * Reading through a bridge rather than seeding the payload is deliberate: the dialog above arms its
 * unsaved-changes prompt on any change to it, so a form that filled in its own blanks at mount
 * would prompt on close without the user having typed anything.
 */
const formModel = computed<Eth2ValidatorFormState>({
  get() {
    return toFormState(get(modelValue));
  },
  set(state: Eth2ValidatorFormState) {
    set(modelValue, state);
  },
});

const { errors, state, touch, validate } = useModelForm<Eth2ValidatorFormState>({
  model: formModel,
  schema,
  serverErrors: errorMessages,
});

defineExpose({
  validate,
});
</script>

<template>
  <div class="grid gap-4 grid-cols-3 mt-3">
    <div class="col-span-3 md:col-span-1">
      <RuiTextField
        v-model.trim="state.validatorIndex"
        data-testid="eth2-validator-index"
        variant="outlined"
        color="primary"
        :disabled="disabled || editMode"
        :label="t('common.validator_index')"
        :error-messages="errors('validatorIndex')"
        @update:model-value="touch('validatorIndex')"
      />
    </div>

    <div class="col-span-3 md:col-span-2 flex gap-4">
      <span class="mt-4">{{ t('common.or') }}</span>
      <RuiTextField
        v-model.trim="state.publicKey"
        data-testid="eth2-public-key"
        class="grow"
        variant="outlined"
        color="primary"
        :disabled="disabled || editMode"
        :label="t('eth2_input.public_key')"
        :error-messages="errors('publicKey')"
        @update:model-value="touch('publicKey')"
      />
    </div>

    <div class="col-span-3 md:col-span-1">
      <RuiTextField
        v-model.trim="state.ownershipPercentage"
        data-testid="eth2-ownership-percentage"
        variant="outlined"
        placeholder="100"
        :disabled="disabled"
        color="primary"
        :label="t('eth2_input.ownership_percentage')"
        :hint="t('eth2_input.ownership.hint')"
        :error-messages="errors('ownershipPercentage')"
        @update:model-value="touch('ownershipPercentage')"
      >
        <template #append>
          {{ t('percentage_display.symbol') }}
        </template>
      </RuiTextField>
    </div>
  </div>
</template>

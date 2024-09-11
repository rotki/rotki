<script setup lang="ts">
import { helpers, requiredUnless } from '@vuelidate/validators';
import { isEmpty } from 'lodash-es';
import useVuelidate from '@vuelidate/core';
import { toMessages } from '@/utils/validation';
import type { Eth2Validator } from '@/types/balances';
import type { ValidationErrors } from '@/types/api/errors';

defineProps<{
  disabled: boolean;
  editMode: boolean;
}>();

const modelValue = defineModel<Eth2Validator>('validator', { required: true });
const errorMessages = defineModel<ValidationErrors>('errorMessages', { required: true });
const validatorIndex = refOptional(useRefPropVModel(modelValue, 'validatorIndex'), '');
const publicKey = refOptional(useRefPropVModel(modelValue, 'publicKey'), '');
const ownershipPercentage = refOptional(useRefPropVModel(modelValue, 'ownershipPercentage'), '');

const { t } = useI18n();

const rules = {
  validatorIndex: {
    requiredUnlessKey: requiredUnless(logicAnd(publicKey)),
    consistOfNumbers: helpers.withMessage(
      t('eth2_input.validator_index.validation'),
      (value: string) => !value || consistOfNumbers(value),
    ),
  },
  publicKey: {
    requiredUnlessIndex: requiredUnless(logicAnd(validatorIndex)),
  },
  ownershipPercentage: {
    percentage: helpers.withMessage(
      t('eth2_input.ownership.validation'),
      (value: string) => !value || (Number(value) > 0 && Number(value) <= 100),
    ),
  },
};

const v$ = useVuelidate(
  rules,
  {
    validatorIndex,
    publicKey,
    ownershipPercentage,
  },
  {
    $autoDirty: true,
    $stopPropagation: true,
    $externalResults: errorMessages,
  },
);

function validate(): Promise<boolean> {
  return get(v$).$validate();
}

watch(errorMessages, (errors) => {
  if (!isEmpty(errors))
    get(v$).$validate();
});

defineExpose({
  validate,
});
</script>

<template>
  <div class="grid gap-4 grid-cols-3 mt-3">
    <div class="col-span-3 md:col-span-1">
      <RuiTextField
        v-model.trim="validatorIndex"
        variant="outlined"
        color="primary"
        :disabled="disabled || editMode"
        :label="t('common.validator_index')"
        :error-messages="toMessages(v$.validatorIndex)"
        @blur="v$.validatorIndex.$touch()"
      />
    </div>

    <div class="col-span-3 md:col-span-2 flex gap-4">
      <span class="mt-4">{{ t('common.or') }}</span>
      <RuiTextField
        v-model.trim="publicKey"
        class="grow"
        variant="outlined"
        color="primary"
        :disabled="disabled || editMode"
        :label="t('eth2_input.public_key')"
        :error-messages="toMessages(v$.publicKey)"
        @blur="v$.publicKey.$touch()"
      />
    </div>

    <div class="col-span-3 md:col-span-1">
      <RuiTextField
        v-model.trim="ownershipPercentage"
        variant="outlined"
        placeholder="100"
        :disabled="disabled"
        color="primary"
        :label="t('eth2_input.ownership_percentage')"
        :hint="t('eth2_input.ownership.hint')"
        :error-messages="toMessages(v$.ownershipPercentage)"
        @blur="v$.ownershipPercentage.$touch()"
      >
        <template #append>
          {{ t('percentage_display.symbol') }}
        </template>
      </RuiTextField>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onlyIfTruthy } from '@rotki/common';
import {
  helpers,
  requiredUnless,
} from '@vuelidate/validators';
import { isEmpty } from 'lodash-es';
import useVuelidate from '@vuelidate/core';
import { toMessages } from '@/utils/validation';
import type { Eth2Validator } from '@/types/balances';
import type { ValidationErrors } from '@/types/api/errors';

const props = defineProps<{
  validator: Eth2Validator | null;
  disabled: boolean;
  errorMessages: ValidationErrors;
}>();

const emit = defineEmits<{
  (e: 'update:validator', validator: Eth2Validator | null): void;
}>();

const { validator, errorMessages } = toRefs(props);
const validatorIndex = ref('');
const publicKey = ref('');
const ownershipPercentage = ref<string>();

function updateProperties() {
  const validatorVal = get(validator);
  set(validatorIndex, validatorVal?.validatorIndex ?? '');
  set(publicKey, validatorVal?.publicKey ?? '');
  set(ownershipPercentage, validatorVal?.ownershipPercentage ?? '');
}

const { t } = useI18n();

const rules = {
  validatorIndex: {
    requiredUnlessKey: requiredUnless(logicAnd(publicKey)),
    consistOfNumbers: helpers.withMessage(
      t('eth2_input.validator_index.validation'),
      (value: string) =>
        !value || consistOfNumbers(value)
      ,
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

watchImmediate(validator, updateProperties);

watch(
  [validatorIndex, publicKey, ownershipPercentage],
  ([validatorIndex, publicKey, ownershipPercentage]) => {
    const validator: Eth2Validator | null
      = validatorIndex || publicKey
        ? {
            validatorIndex: onlyIfTruthy(validatorIndex)?.trim(),
            publicKey: onlyIfTruthy(publicKey)?.trim(),
            ownershipPercentage: onlyIfTruthy(ownershipPercentage)?.trim(),
          }
        : null;
    emit('update:validator', validator);
  },
);

defineExpose({
  validate,
});
</script>

<template>
  <div class="grid gap-4 grid-cols-3 mt-3">
    <div class="col-span-3 md:col-span-1">
      <RuiTextField
        v-model="validatorIndex"
        variant="outlined"
        color="primary"
        :disabled="disabled"
        :label="t('common.validator_index')"
        :error-messages="toMessages(v$.validatorIndex)"
        @blur="v$.validatorIndex.$touch()"
      />
    </div>

    <div class="col-span-3 md:col-span-2 flex gap-4">
      <span class="mt-4">{{ t('common.or') }}</span>
      <RuiTextField
        v-model="publicKey"
        class="grow"
        variant="outlined"
        color="primary"
        :disabled="disabled"
        :label="t('eth2_input.public_key')"
        :error-messages="toMessages(v$.publicKey)"
        @blur="v$.publicKey.$touch()"
      />
    </div>

    <div class="col-span-3 md:col-span-1">
      <AmountInput
        v-model="ownershipPercentage"
        variant="outlined"
        placeholder="100"
        :label="t('eth2_input.ownership_percentage')"
        :hint="t('eth2_input.ownership.hint')"
        :error-messages="toMessages(v$.ownershipPercentage)"
        @blur="v$.ownershipPercentage.$touch()"
      >
        <template #append>
          {{ t('percentage_display.symbol') }}
        </template>
      </AmountInput>
    </div>
  </div>
</template>

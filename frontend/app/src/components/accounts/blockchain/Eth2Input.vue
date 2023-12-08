<script setup lang="ts">
import { onlyIfTruthy } from '@rotki/common';
import {
  and,
  helpers,
  maxValue,
  minValue,
  requiredUnless
} from '@vuelidate/validators';
import { isEmpty } from 'lodash-es';
import { type Eth2Validator } from '@/types/balances';
import { type ValidationErrors } from '@/types/api/errors';
import { toMessages } from '@/utils/validation';

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

const updateProperties = (validator: Eth2Validator | null) => {
  validatorIndex.value = validator?.validatorIndex ?? '';
  publicKey.value = validator?.publicKey ?? '';
  ownershipPercentage.value = validator?.ownershipPercentage ?? '';
};

const { t } = useI18n();

const rules = {
  validatorIndex: {
    requiredUnlessKey: requiredUnless(logicAnd(publicKey))
  },
  publicKey: {
    requiredUnlessIndex: requiredUnless(logicAnd(validatorIndex))
  },
  ownershipPercentage: {
    percentage: helpers.withMessage(
      t('eth2_input.ownership.validation'),
      and(minValue(0), maxValue(100))
    )
  }
};

const { setValidation } = useAccountDialog();

const v$ = setValidation(
  rules,
  {
    validatorIndex,
    publicKey,
    ownershipPercentage
  },
  {
    $autoDirty: true,
    $stopPropagation: true,
    $externalResults: errorMessages
  }
);

watch(errorMessages, errors => {
  if (!isEmpty(errors)) {
    get(v$).$validate();
  }
});

onMounted(() => updateProperties(validator.value));

watch(validator, updateProperties);

watch(
  [validatorIndex, publicKey, ownershipPercentage],
  ([validatorIndex, publicKey, ownershipPercentage]) => {
    const validator: Eth2Validator | null =
      validatorIndex || publicKey
        ? {
            validatorIndex: onlyIfTruthy(validatorIndex)?.trim(),
            publicKey: onlyIfTruthy(publicKey)?.trim(),
            ownershipPercentage: onlyIfTruthy(ownershipPercentage)?.trim()
          }
        : null;
    emit('update:validator', validator);
  }
);
</script>

<template>
  <div class="grid gap-4 grid-cols-2">
    <div class="col-span-2">
      <RuiTextField
        v-model="publicKey"
        variant="outlined"
        color="primary"
        :disabled="disabled"
        :label="t('eth2_input.public_key')"
        :error-messages="toMessages(v$.publicKey)"
        @blur="v$.publicKey.$touch()"
      />
    </div>
    <div class="col-span-2 md:col-span-1">
      <AmountInput
        v-model="validatorIndex"
        outlined
        :disabled="disabled"
        :label="t('common.validator_index')"
        :error-messages="toMessages(v$.validatorIndex)"
        @blur="v$.validatorIndex.$touch()"
      />
    </div>

    <div class="col-span-2 md:col-span-1">
      <AmountInput
        v-model="ownershipPercentage"
        outlined
        placeholder="100"
        :label="t('eth2_input.ownership_percentage')"
        :hint="t('eth2_input.ownership.hint')"
        suffix="%"
        :error-messages="toMessages(v$.ownershipPercentage)"
        @blur="v$.ownershipPercentage.$touch()"
      />
    </div>
  </div>
</template>

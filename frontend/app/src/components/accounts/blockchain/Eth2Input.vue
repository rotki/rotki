<script setup lang="ts">
import { onlyIfTruthy } from '@rotki/common';
import useVuelidate from '@vuelidate/core';
import {
  and,
  helpers,
  maxValue,
  minValue,
  requiredUnless
} from '@vuelidate/validators';
import isEmpty from 'lodash/isEmpty';
import { type Eth2Validator } from '@/types/balances';
import { type ValidationErrors } from '@/types/api/errors';
import { toMessages } from '@/utils/validation-errors';

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

const { tc } = useI18n();

const rules = {
  validatorIndex: {
    requiredUnlessKey: requiredUnless(logicAnd(publicKey))
  },
  publicKey: {
    requiredUnlessIndex: requiredUnless(logicAnd(validatorIndex))
  },
  ownershipPercentage: {
    percentage: helpers.withMessage(
      tc('eth2_input.ownership.validation'),
      and(minValue(0), maxValue(100))
    )
  }
};

const v$ = useVuelidate(
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
  <v-row>
    <v-col cols="12" md="4" lg="2">
      <v-text-field
        v-model="validatorIndex"
        outlined
        type="number"
        :disabled="disabled"
        :label="tc('common.validator_index')"
        :error-messages="toMessages(v$.validatorIndex)"
        @blur="v$.validatorIndex.$touch()"
      />
    </v-col>
    <v-col cols="12" md="6" lg="8">
      <v-text-field
        v-model="publicKey"
        outlined
        :disabled="disabled"
        :label="tc('eth2_input.public_key')"
        :error-messages="toMessages(v$.publicKey)"
        @blur="v$.publicKey.$touch()"
      />
    </v-col>
    <v-col cols="12" md="2" lg="2">
      <v-text-field
        v-model="ownershipPercentage"
        outlined
        placeholder="100"
        :label="tc('eth2_input.ownership_percentage')"
        persistent-hint
        :hint="tc('eth2_input.ownership.hint')"
        suffix="%"
        :error-messages="toMessages(v$.ownershipPercentage)"
        @blur="v$.ownershipPercentage.$touch()"
      />
    </v-col>
  </v-row>
</template>

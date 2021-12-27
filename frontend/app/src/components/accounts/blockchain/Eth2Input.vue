<template>
  <v-row>
    <v-col cols="12" md="4" lg="2">
      <v-text-field
        v-model="validatorIndex"
        outlined
        type="number"
        :disabled="disabled"
        :label="$t('eth2_input.validator_index')"
      />
    </v-col>
    <v-col cols="12" md="6" lg="8">
      <v-text-field
        v-model="publicKey"
        outlined
        :disabled="disabled"
        :label="$t('eth2_input.public_key')"
      />
    </v-col>
    <v-col cols="12" md="2" lg="2">
      <v-text-field
        v-model="percentage"
        outlined
        :rules="percentageRules"
        placeholder="100"
        :label="$t('eth2_input.ownership_percentage')"
        persistent-hint
        :hint="$t('eth2_input.ownership.hint')"
        suffix="%"
      />
    </v-col>
  </v-row>
</template>

<script lang="ts">
import { onlyIfTruthy } from '@rotki/common';
import {
  computed,
  defineComponent,
  onMounted,
  PropType,
  ref,
  toRefs,
  watch
} from '@vue/composition-api';
import i18n from '@/i18n';
import { Eth2Validator } from '@/types/balances';

const isValid = (percentage: string) => {
  const perc = parseFloat(percentage);
  return isFinite(perc) && perc >= 0 && perc <= 100;
};

export default defineComponent({
  name: 'Eth2Input',
  props: {
    validator: {
      required: false,
      type: Object as PropType<Eth2Validator | null>,
      default: null
    },
    disabled: {
      required: false,
      type: Boolean,
      default: false
    }
  },
  emits: ['update:validator'],
  setup(props, { emit }) {
    const { validator } = toRefs(props);
    const validatorIndex = ref('');
    const publicKey = ref('');
    const percentage = ref<string>();

    const updateValidator = (validator: Eth2Validator | null) => {
      emit('update:validator', validator);
    };

    const updateProperties = (validator: Eth2Validator | null) => {
      validatorIndex.value = validator?.validatorIndex ?? '';
      publicKey.value = validator?.publicKey ?? '';
      percentage.value = validator?.ownershipPercentage ?? '';
    };
    onMounted(() => updateProperties(validator.value));
    watch(validator, updateProperties);

    watch(
      [validatorIndex, publicKey, percentage],
      ([validatorIndex, publicKey, ownershipPercentage]) => {
        const validator: Eth2Validator | null =
          validatorIndex || publicKey
            ? {
                validatorIndex: onlyIfTruthy(validatorIndex)?.trim(),
                publicKey: onlyIfTruthy(publicKey)?.trim(),
                ownershipPercentage: onlyIfTruthy(ownershipPercentage)?.trim()
              }
            : null;
        updateValidator(validator);
      }
    );

    const percentageRules = computed(() => [
      (v?: string) =>
        !v || isValid(v) || i18n.t('eth2_input.ownership.validation').toString()
    ]);

    return {
      validatorIndex,
      publicKey,
      percentage,
      percentageRules
    };
  }
});
</script>

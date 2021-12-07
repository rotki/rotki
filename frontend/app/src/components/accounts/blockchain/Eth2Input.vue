<template>
  <v-row>
    <v-col cols="12" md="4" lg="2">
      <v-text-field
        v-model="validatorIndex"
        outlined
        type="number"
        label="Validator Index"
      />
    </v-col>
    <v-col cols="12" md="8" lg="10">
      <v-text-field v-model="publicKey" outlined label="Public Key" />
    </v-col>
  </v-row>
</template>

<script lang="ts">
import { onlyIfTruthy } from '@rotki/common';
import {
  defineComponent,
  PropType,
  ref,
  toRefs,
  watch
} from '@vue/composition-api';
import { Eth2Validator } from '@/types/balances';

export default defineComponent({
  name: 'Eth2Input',
  props: {
    validator: {
      required: false,
      type: Object as PropType<Eth2Validator | null>,
      default: null
    }
  },
  emits: ['update:validator'],
  setup(props, { emit }) {
    const { validator } = toRefs(props);
    const validatorIndex = ref('');
    const publicKey = ref('');

    const updateValidator = (validator: Eth2Validator | null) => {
      emit('update:validator', validator);
    };

    watch(validator, validator => {
      validatorIndex.value = validator?.validatorIndex ?? '';
      publicKey.value = validator?.publicKey ?? '';
    });

    watch([validatorIndex, publicKey], ([validatorIndex, publicKey]) => {
      const validator: Eth2Validator | null =
        validatorIndex || publicKey
          ? {
              validatorIndex: onlyIfTruthy(validatorIndex)?.trim(),
              publicKey: onlyIfTruthy(publicKey)?.trim()
            }
          : null;
      updateValidator(validator);
    });

    return {
      validatorIndex,
      publicKey
    };
  }
});
</script>

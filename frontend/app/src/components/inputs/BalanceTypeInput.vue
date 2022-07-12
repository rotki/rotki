<template>
  <v-select
    :value="value"
    :items="balanceTypes"
    v-bind="$attrs"
    @input="input"
  />
</template>

<script lang="ts">
import { defineComponent, PropType } from '@vue/composition-api';
import i18n from '@/i18n';
import { BalanceType } from '@/services/balances/types';

const balanceTypes = [
  {
    value: BalanceType.ASSET,
    text: i18n.t('manual_balances_form.type.asset')
  },
  {
    value: BalanceType.LIABILITY,
    text: i18n.t('manual_balances_form.type.liability')
  }
];

export default defineComponent({
  name: 'BalanceTypeInput',
  props: {
    value: {
      required: true,
      type: String as PropType<BalanceType>
    }
  },
  emits: ['input'],
  setup(_, { emit }) {
    const input = (value: BalanceType) => {
      emit('input', value);
    };

    return {
      balanceTypes,
      input
    };
  }
});
</script>

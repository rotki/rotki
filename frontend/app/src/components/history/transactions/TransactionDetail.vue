<template>
  <card>
    <template #title>
      {{ $t('transactions.details.title') }}
    </template>
    <div class="pt-4">
      <v-row class="pb-2">
        <v-col cols="2" class="font-weight-medium">
          {{ $t('transactions.details.gas_fee') }}
        </v-col>
        <v-col cols="10">
          <amount-display :value="gasFee" asset="ETH" />
        </v-col>
      </v-row>
      <v-divider class="pb-2" />
      <v-row class="pb-2">
        <v-col cols="2" class="font-weight-medium">
          {{ $t('transactions.details.gas_limit') }}
        </v-col>
        <v-col cols="10">
          <amount-display :value="transaction.gas" integer />
        </v-col>
      </v-row>
      <v-divider class="pb-2" />
      <v-row class="pb-2">
        <v-col cols="2" class="font-weight-medium">
          {{ $t('transactions.details.gas_used') }}
        </v-col>
        <v-col cols="10">
          <amount-display :value="transaction.gasUsed" integer />
        </v-col>
      </v-row>
      <v-divider class="pb-2" />
      <v-row class="pb-2">
        <v-col cols="2" class="font-weight-medium">
          {{ $t('transactions.details.gas_price') }}
        </v-col>
        <v-col cols="10">
          <amount-display :value="toGwei(transaction.gasPrice)" asset="Gwei" />
        </v-col>
      </v-row>
      <v-divider class="pb-2" />
      <v-row class="pb-2">
        <v-col cols="2" class="font-weight-medium">
          {{ $t('transactions.details.nonce') }}
        </v-col>
        <v-col cols="10">{{ transaction.nonce }}</v-col>
      </v-row>
      <v-divider class="pb-2" />
      <v-row class="pb-2">
        <v-col cols="2" class="font-weight-medium">
          {{ $t('transactions.details.input_data') }}
        </v-col>
        <v-col cols="10">
          <textarea
            :value="transaction.inputData"
            readonly
            spellcheck="false"
            class="text--secondary"
            :class="$style['input-data']"
          />
        </v-col>
      </v-row>
    </div>
    <template #buttons>
      <v-spacer />
      <v-btn color="primary" class="px-6" @click="close">
        {{ $t('transactions.details.close') }}
      </v-btn>
    </template>
  </card>
</template>
<script lang="ts">
import { BigNumber } from '@rotki/common';
import {
  computed,
  defineComponent,
  PropType,
  toRefs
} from '@vue/composition-api';
import { get } from '@vueuse/core';
import { EthTransactionEntry } from '@/store/history/types';
import { toUnit, Unit } from '@/utils/calculation';

export default defineComponent({
  name: 'TransactionDetail',
  props: {
    transaction: {
      required: true,
      type: Object as PropType<EthTransactionEntry>
    }
  },
  emits: ['close'],
  setup(props, { emit }) {
    const { transaction } = toRefs(props);

    const toGwei = (value: BigNumber) => {
      return toUnit(value, Unit.GWEI);
    };

    const gasFee = computed<BigNumber>(() => {
      const tx = get(transaction);
      return toUnit(tx.gasPrice.multipliedBy(tx.gasUsed), Unit.ETH);
    });

    const close = () => {
      emit('close');
    };

    return {
      toGwei,
      gasFee,
      close
    };
  }
});
</script>
<style module lang="scss">
.input-data {
  background-color: var(--v-rotki-light-grey-lighten1);
  border: var(--v-rotki-light-grey-darken1) solid thin;
  border-radius: 4px;
  font-family: 'Roboto Mono', monospace;
  width: 100%;
  height: 80px;
  padding: 16px;
  font-size: 14px;
}
</style>

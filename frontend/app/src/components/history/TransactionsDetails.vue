<template>
  <table-expand-container visible :colspan="colspan">
    <template #title>
      {{ $t('transaction_details.title') }}
    </template>
    <v-row class="pb-2">
      <v-col cols="2" class="font-weight-medium">
        {{ $t('transaction_details.gas') }}
      </v-col>
      <v-col cols="10">
        <amount-display :value="transaction.gas" integer />
      </v-col>
    </v-row>
    <v-divider class="pb-2" />
    <v-row class="pb-2">
      <v-col cols="2" class="font-weight-medium">
        {{ $t('transaction_details.gas_used') }}
      </v-col>
      <v-col cols="10">
        <amount-display :value="transaction.gasUsed" integer />
      </v-col>
    </v-row>
    <v-divider class="pb-2" />
    <v-row class="pb-2">
      <v-col cols="2" class="font-weight-medium">
        {{ $t('transaction_details.gas_price') }}
      </v-col>
      <v-col cols="10">
        <amount-display :value="toGwei(transaction.gasPrice)" asset="Gwei" />
      </v-col>
    </v-row>
    <v-divider class="pb-2" />
    <v-row class="pb-2">
      <v-col cols="2" class="font-weight-medium">
        {{ $t('transaction_details.nonce') }}
      </v-col>
      <v-col cols="10">{{ transaction.nonce }}</v-col>
    </v-row>
    <v-divider class="pb-2" />
    <v-row class="pb-2">
      <v-col cols="2" class="font-weight-medium">
        {{ $t('transaction_details.input_data') }}
      </v-col>
      <v-col cols="10">
        <textarea
          v-model="transaction.inputData"
          readonly
          spellcheck="false"
          class="transaction-details__data text--secondary"
        />
      </v-col>
    </v-row>
  </table-expand-container>
</template>

<script lang="ts">
import { BigNumber } from '@rotki/common';
import { Component, Prop, Vue } from 'vue-property-decorator';
import TableExpandContainer from '@/components/helper/table/TableExpandContainer.vue';
import { EthTransaction } from '@/services/history/types';
import { toUnit, Unit } from '@/utils/calculation';

@Component({
  components: { TableExpandContainer }
})
export default class TransactionDetails extends Vue {
  @Prop({ required: true })
  transaction!: EthTransaction;
  @Prop({ required: true, type: Number })
  colspan!: number;

  toGwei(value: BigNumber) {
    return toUnit(value, Unit.GWEI);
  }
}
</script>

<style scoped lang="scss">
@import '~@/scss/scroll';

.transaction-details {
  &__data {
    background-color: var(--v-rotki-light-grey-lighten1);
    border: var(--v-rotki-light-grey-darken1) solid thin;
    border-radius: 4px;
    font-family: 'Roboto Mono', monospace;
    width: 100%;
    height: 80px;
    padding: 16px;
    font-size: 14px;
    @extend .themed-scrollbar;
  }
}
</style>

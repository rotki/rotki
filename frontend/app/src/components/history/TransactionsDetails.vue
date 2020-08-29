<template>
  <v-container>
    <h2 class="mt-1 mb-2">
      {{ $t('transaction_details.title') }}
    </h2>
    <v-row>
      <v-col cols="2" class="font-weight-medium">
        {{ $t('transaction_details.gas') }}
      </v-col>
      <v-col cols="10">
        <amount-display :value="transaction.gas" integer />
      </v-col>
    </v-row>
    <v-divider />
    <v-row>
      <v-col cols="2" class="font-weight-medium">
        {{ $t('transaction_details.gas_used') }}
      </v-col>
      <v-col cols="10">
        <amount-display :value="transaction.gasUsed" integer />
      </v-col>
    </v-row>
    <v-divider />
    <v-row>
      <v-col cols="2" class="font-weight-medium">
        {{ $t('transaction_details.gas_price') }}
      </v-col>
      <v-col cols="10">
        <amount-display :value="toEth(transaction.gasPrice)" asset="ETH" />
      </v-col>
    </v-row>
    <v-divider />
    <v-row>
      <v-col cols="2" class="font-weight-medium">
        {{ $t('transaction_details.nonce') }}
      </v-col>
      <v-col cols="10">{{ transaction.nonce }}</v-col>
    </v-row>
    <v-divider />
    <v-row>
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
  </v-container>
</template>

<script lang="ts">
import { Component, Vue, Prop } from 'vue-property-decorator';
import { EthTransaction } from '@/services/history/types';
import { toEth } from '@/utils/calculation';

@Component({})
export default class TransactionDetails extends Vue {
  @Prop({ required: true })
  transaction!: EthTransaction;

  toEth = toEth;
}
</script>

<style scoped lang="scss">
@import '~@/scss/scroll';

.transaction-details {
  &__data {
    @extend .themed-scrollbar;
    background-color: var(--v-rotki-light-grey-lighten1);
    border: var(--v-rotki-light-grey-darken1) solid thin;
    border-radius: 4px;
    font-family: 'Roboto Mono', monospace;
    width: 100%;
    height: 80px;
    padding: 16px;
    font-size: 14px;
  }
}
</style>

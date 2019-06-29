<template xmlns:v-slot="http://www.w3.org/1999/XSL/Transform">
  <div>
    <v-layout row>
      <v-flex>
        <h3>{{ name }} balances per Account</h3>
      </v-flex>
    </v-layout>
    <v-data-table :headers="headers" :items="balances">
      <template v-slot:items="props">
        <td>
          {{ props.item.account }}
        </td>
        <td>
          {{ props.item.amount | formatPrice(floatingPrecision) }}
        </td>
        <td>
          {{ props.item.usdValue | formatPrice(floatingPrecision) }}
        </td>
      </template>
    </v-data-table>
  </div>
</template>

<script lang="ts">
import { Component, Prop, Vue } from 'vue-property-decorator';
import { AccountBalance } from '@/model/blockchain-balances';

@Component({})
export default class PerAccountEth extends Vue {
  @Prop({ required: true })
  balances!: AccountBalance[];
  @Prop({ required: true })
  name!: string;

  headers = [
    { text: 'Account', value: 'account' },
    { text: this.name, value: 'amount' },
    { text: 'USD Value', value: 'usdValue' }
  ];
}
</script>

<style scoped></style>

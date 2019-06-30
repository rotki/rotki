<template xmlns:v-slot="http://www.w3.org/1999/XSL/Transform">
  <div class="balance-table">
    <v-layout row>
      <v-flex>
        <h3 class="text-xs-center">{{ title }}</h3>
      </v-flex>
    </v-layout>
    <v-data-table :headers="headers" :items="balances">
      <template v-slot:items="props">
        <td>
          <crypto-icon :symbol="props.item.asset"></crypto-icon>
          {{ props.item.asset }}
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
import { AssetBalance } from '@/model/blockchain-balances';
import { mapState } from 'vuex';

@Component({
  computed: mapState(['floatingPrecision'])
})
export default class AssetBalances extends Vue {
  @Prop({ required: true })
  balances!: AssetBalance[];
  @Prop({ required: true })
  title!: string;

  floatingPrecision!: number;

  headers = [
    { text: 'Asset', value: 'asset' },
    { text: 'Amount', value: 'amount' },
    { text: 'USD Value', value: 'usdValue' }
  ];
}
</script>

<style scoped lang="scss">
.balance-table {
  margin-top: 16px;
  margin-bottom: 16px;
}
</style>

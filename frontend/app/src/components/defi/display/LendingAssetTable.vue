<template>
  <v-data-table
    :items="assets"
    :headers="headers"
    :loading="loading"
    sort-desc
    sort-by="balance.usdValue"
  >
    <template #item.asset="{ item }">
      <span class="d-flex flex-row align-center">
        <crypto-icon
          width="26px"
          :symbol="item.asset"
          class="mr-2"
        ></crypto-icon>
        {{ item.asset }}
      </span>
    </template>
    <template #item.protocol="{ item }">
      <span>
        <v-img
          width="55px"
          contain
          max-height="24px"
          :src="require(`@/assets/images/defi/${item.protocol}.svg`)"
        />
      </span>
    </template>
    <template #item.balance.amount="{ item }">
      <amount-display :value="item.balance.amount"></amount-display>
    </template>
    <template #item.balance.usdValue="{ item }">
      <amount-display
        fiat-currency="USD"
        :value="item.balance.usdValue"
      ></amount-display>
    </template>
    <template #item.apy="{ item }">
      {{ item.effectiveInterestRate ? item.effectiveInterestRate : '-' }}
    </template>
    <template #item.address="{item}">
      <hash-link
        :text="item.address"
        class="d-inline font-weight-medium"
      ></hash-link>
    </template>
    <template #header.balance.usdValue>
      {{ currency.ticker_symbol }} Value
    </template>
  </v-data-table>
</template>

<script lang="ts">
import { Component, Prop, Vue } from 'vue-property-decorator';
import { mapGetters } from 'vuex';
import CryptoIcon from '@/components/CryptoIcon.vue';
import AmountDisplay from '@/components/display/AmountDisplay.vue';
import HashLink from '@/components/helper/HashLink.vue';
import { Currency } from '@/model/currency';
import { DefiBalance } from '@/store/defi/types';

@Component({
  components: { HashLink, AmountDisplay, CryptoIcon },
  computed: {
    ...mapGetters('session', ['currency'])
  }
})
export default class LendingAssetTable extends Vue {
  @Prop({ required: true })
  assets!: DefiBalance[];
  @Prop({ required: false, type: Boolean })
  loading!: boolean;
  currency!: Currency;

  headers = [
    { text: 'Asset', value: 'asset' },
    { text: 'Protocol', value: 'protocol' },
    { text: 'Address', value: 'address' },
    { text: 'Amount', value: 'balance.amount' },
    { text: 'USD Value', value: 'balance.usdValue' },
    { text: 'Effective Interest Rate', value: 'effectiveInterestRate' }
  ];
}
</script>

<style scoped></style>

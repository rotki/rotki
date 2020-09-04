<template>
  <v-data-table
    :items="assets"
    :headers="headers"
    :loading="loading"
    :footer-props="footerProps"
    sort-desc
    sort-by="balance.usdValue"
  >
    <template #item.asset="{ item }">
      <span class="d-flex flex-row align-center">
        <crypto-icon size="26px" :symbol="item.asset" class="mr-2" />
        {{ item.asset }}
      </span>
    </template>
    <template #item.protocol="{ item }">
      <div class="d-flex flex-row lending-asset-table__protocol__">
        <defi-protocol-icon
          :protocol="item.protocol"
          class="lending-asset-table__protocol__icon"
        />
        <span class="lending-asset-table__protocol__name align-self-center">
          {{
            item.protocol === 'makerdao'
              ? 'MakerDAO DSR'
              : item.protocol | capitalize
          }}
        </span>
      </div>
    </template>
    <template #item.balance.amount="{ item }">
      <amount-display :value="item.balance.amount" />
    </template>
    <template #item.balance.usdValue="{ item }">
      <amount-display
        fiat-currency="USD"
        :value="item.balance.usdValue"
        show-currency="symbol"
      />
    </template>
    <template #item.apy="{ item }">
      {{ item.effectiveInterestRate ? item.effectiveInterestRate : '-' }}
    </template>
    <template #item.address="{item}">
      <hash-link :text="item.address" class="d-inline font-weight-medium" />
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
import DefiProtocolIcon from '@/components/defi/display/DefiProtocolIcon.vue';
import AmountDisplay from '@/components/display/AmountDisplay.vue';
import HashLink from '@/components/helper/HashLink.vue';
import { footerProps } from '@/config/datatable.common';
import { Currency } from '@/model/currency';
import { DefiBalance } from '@/store/defi/types';

@Component({
  components: { DefiProtocolIcon, HashLink, AmountDisplay, CryptoIcon },
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

  footerProps = footerProps;

  headers = [
    { text: 'Asset', value: 'asset' },
    { text: 'Protocol', value: 'protocol' },
    { text: 'Address', value: 'address' },
    { text: 'Amount', value: 'balance.amount', align: 'end' },
    { text: 'USD Value', value: 'balance.usdValue', align: 'end' },
    {
      text: 'Effective Interest Rate',
      value: 'effectiveInterestRate',
      align: 'end'
    }
  ];
}
</script>

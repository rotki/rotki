<template>
  <v-card>
    <v-card-title>
      <card-title> {{ $t('asset-locations.title') }}</card-title>
    </v-card-title>
    <v-card-text>
      <v-sheet outlined rounded>
        <v-data-table
          :headers="headers"
          :items="assetLocations"
          sort-by="balance.amount"
          sort-desc
          :footer-props="footerProps"
        >
          <template #item.location="{ item }">
            <location-display :identifier="item.location" />
          </template>
          <template #item.address="{ item }">
            <labeled-address-display
              v-if="item.address"
              :account="account(item.address)"
            />
          </template>
          <template #item.balance.amount="{ item }">
            <amount-display :value="item.balance.amount" />
          </template>
          <template #item.balance.usdValue="{ item }">
            <amount-display
              :fiat-currency="identifier"
              :amount="item.balance.amount"
              :value="item.balance.usdValue"
              show-currency="symbol"
            />
          </template>
        </v-data-table>
      </v-sheet>
    </v-card-text>
  </v-card>
</template>

<script lang="ts">
import { Component, Prop, Vue } from 'vue-property-decorator';
import { DataTableHeader } from 'vuetify';
import { mapGetters } from 'vuex';
import LabeledAddressDisplay from '@/components/display/LabeledAddressDisplay.vue';
import CardTitle from '@/components/typography/CardTitle.vue';
import { footerProps } from '@/config/datatable.common';
import { CURRENCY_USD } from '@/data/currencies';
import { AssetBreakdown } from '@/store/balances/types';
import { GeneralAccount } from '@/typing/types';

@Component({
  components: { LabeledAddressDisplay, CardTitle },
  computed: {
    ...mapGetters('balances', ['breakdown', 'account']),
    ...mapGetters('session', ['currencySymbol'])
  }
})
export default class AssetLocations extends Vue {
  readonly footerProps = footerProps;
  get headers(): DataTableHeader[] {
    return [
      {
        text: this.$t('asset_locations.header.location').toString(),
        value: 'location',
        align: 'center',
        width: '120px'
      },
      {
        text: this.$t('asset_locations.header.address').toString(),
        value: 'address'
      },
      {
        text: this.$t('asset_locations.header.amount').toString(),
        value: 'balance.amount',
        align: 'end'
      },
      {
        text: this.$t('asset_locations.header.value', {
          symbol: this.currencySymbol ?? CURRENCY_USD
        }).toString(),
        value: 'balance.usdValue',
        align: 'end'
      }
    ];
  }

  @Prop({ required: true, type: String })
  identifier!: string;

  breakdown!: (asset: string) => AssetBreakdown[];
  account!: (address: string) => GeneralAccount | undefined;
  currencySymbol!: string;

  get assetLocations(): AssetBreakdown[] {
    return this.breakdown(this.identifier);
  }
}
</script>

<style scoped lang="scss">
::v-deep {
  th {
    &:first-child {
      span {
        padding-left: 16px;
      }
    }
  }
}
</style>

<template>
  <v-card>
    <v-card-title>
      <card-title> {{ $t('asset_locations.title') }}</card-title>
    </v-card-title>
    <v-card-text>
      <v-sheet outlined rounded>
        <data-table
          :headers="headers"
          :items="assetLocations"
          sort-by="balance.amount"
          :loading="detailsLoading"
        >
          <template #item.location="{ item }">
            <location-display :identifier="item.location" />
          </template>
          <template #item.label="{ item }">
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
          <template #item.percentage="{ item }">
            <percentage-display :value="getPercentage(item.balance.usdValue)" />
          </template>
        </data-table>
      </v-sheet>
    </v-card-text>
  </v-card>
</template>

<script lang="ts">
import { default as BigNumber } from 'bignumber.js';
import { Component, Prop, Vue } from 'vue-property-decorator';
import { DataTableHeader } from 'vuetify';
import { mapGetters } from 'vuex';
import LabeledAddressDisplay from '@/components/display/LabeledAddressDisplay.vue';
import DataTable from '@/components/helper/DataTable.vue';
import CardTitle from '@/components/typography/CardTitle.vue';
import { CURRENCY_USD } from '@/data/currencies';
import { AssetBreakdown, AssetPriceInfo } from '@/store/balances/types';
import { GeneralAccount } from '@/typing/types';

@Component({
  components: { DataTable, LabeledAddressDisplay, CardTitle },
  computed: {
    ...mapGetters('balances', ['breakdown', 'account', 'assetPriceInfo']),
    ...mapGetters('session', ['currencySymbol']),
    ...mapGetters(['detailsLoading'])
  }
})
export default class AssetLocations extends Vue {
  get headers(): DataTableHeader[] {
    return [
      {
        text: this.$t('asset_locations.header.location').toString(),
        value: 'location',
        align: 'center',
        width: '120px'
      },
      {
        text: this.$t('asset_locations.header.account').toString(),
        value: 'label'
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
      },
      {
        text: this.$t('asset_locations.header.percentage').toString(),
        value: 'percentage',
        sortable: false,
        align: 'end'
      }
    ];
  }

  @Prop({ required: true, type: String })
  identifier!: string;

  breakdown!: (asset: string) => AssetBreakdown[];
  account!: (address: string) => GeneralAccount | undefined;
  currencySymbol!: string;
  detailsLoading!: boolean;
  assetPriceInfo!: (asset: string) => AssetPriceInfo;

  get totalUsdValue(): BigNumber {
    return this.assetPriceInfo(this.identifier).usdValue;
  }

  get assetLocations(): (AssetBreakdown & { readonly label: string })[] {
    return this.breakdown(this.identifier).map(value => ({
      label: this.account(value.address)?.label ?? '',
      ...value
    }));
  }

  getPercentage(usdValue: BigNumber): string {
    return usdValue.div(this.totalUsdValue).multipliedBy(100).toFixed(2);
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

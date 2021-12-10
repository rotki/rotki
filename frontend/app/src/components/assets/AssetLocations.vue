<template>
  <card>
    <template #title>
      {{ $t('asset_locations.title') }}
    </template>
    <template #actions>
      <v-row no-gutters justify="end">
        <v-col cols="12" md="6" lg="4">
          <tag-filter v-model="onlyTags" />
        </v-col>
      </v-row>
    </template>
    <data-table
      :headers="headers"
      :items="visibleAssetLocations"
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
        <tag-display :tags="item.tags" />
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
  </card>
</template>

<script lang="ts">
import { BigNumber } from '@rotki/common';
import { GeneralAccount } from '@rotki/common/lib/account';
import { Component, Prop, Vue } from 'vue-property-decorator';
import { DataTableHeader } from 'vuetify';
import { mapGetters } from 'vuex';
import LabeledAddressDisplay from '@/components/display/LabeledAddressDisplay.vue';
import DataTable from '@/components/helper/DataTable.vue';
import TagFilter from '@/components/inputs/TagFilter.vue';
import TagDisplay from '@/components/tags/TagDisplay.vue';
import CardTitle from '@/components/typography/CardTitle.vue';
import { CURRENCY_USD } from '@/data/currencies';
import { AssetBreakdown, AssetPriceInfo } from '@/store/balances/types';

@Component({
  components: {
    DataTable,
    LabeledAddressDisplay,
    CardTitle,
    TagDisplay,
    TagFilter
  },
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
  onlyTags: string[] = [];

  get totalUsdValue(): BigNumber {
    return this.assetPriceInfo(this.identifier).usdValue;
  }

  get assetLocations(): (AssetBreakdown & { readonly label: string })[] {
    return this.breakdown(this.identifier).map(value => ({
      label: this.account(value.address)?.label ?? '',
      ...value
    }));
  }

  get visibleAssetLocations(): (AssetBreakdown & { readonly label: string })[] {
    if (this.onlyTags.length === 0) {
      return this.assetLocations;
    }
    return this.assetLocations.filter(assetLocation => {
      if (assetLocation.tags) {
        return this.onlyTags.every(tag => assetLocation.tags?.includes(tag));
      }
    });
  }

  getPercentage(usdValue: BigNumber): string {
    const percentage = this.totalUsdValue.isZero()
      ? 0
      : usdValue.div(this.totalUsdValue).multipliedBy(100);
    return percentage.toFixed(2);
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

.asset-locations-table {
  &__tag {
    margin-right: 8px;
    margin-bottom: 2px;
  }
}
</style>

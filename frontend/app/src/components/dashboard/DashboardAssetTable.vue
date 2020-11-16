<template>
  <v-card>
    <v-row no-gutters class="pa-3 secondary--text">
      <v-toolbar-title class="font-weight-medium">
        {{ title }}
      </v-toolbar-title>
      <v-spacer />
      <v-text-field
        v-model="search"
        append-icon="mdi-magnify"
        :label="$t('dashboard_asset_table.search')"
        class="pa-0 ma-0"
        single-line
        hide-details
      />
    </v-row>
    <v-card-text>
      <v-data-table
        class="dashboard-asset-table__balances"
        :headers="headers"
        :items="balances"
        :search="search"
        :loading="loading"
        sort-by="usdValue"
        sort-desc
        :footer-props="footerProps"
      >
        <template #header.usdValue>
          {{
            $t('dashboard_asset_table.headers.value', {
              symbol: currencySymbol
            })
          }}
        </template>
        <template #item.asset="{ item }">
          <asset-details :asset="item.asset" />
        </template>
        <template #item.amount="{ item }">
          <amount-display :value="item.amount" />
        </template>
        <template #item.usdValue="{ item }">
          <amount-display
            show-currency="symbol"
            :fiat-currency="item.asset"
            :amount="item.amount"
            :value="item.usdValue"
          />
        </template>
        <template #item.percentage="{ item }">
          <percentage-display :value="percentage(item.usdValue, total)" />
        </template>
        <template #no-results>
          <span class="grey--text text--darken-2">
            {{
              $t('dashboard_asset_table.no_search_result', {
                search
              })
            }}
          </span>
        </template>
        <template v-if="balances.length > 0 && search.length < 1" #body.append>
          <tr class="dashboard-asset-table__balances__total font-weight-medium">
            <td colspan="2">{{ $t('dashboard_asset_table.total') }}</td>
            <td class="text-end">
              <amount-display
                :fiat-currency="currencySymbol"
                :value="
                  balances
                    | aggregateTotal(
                      currencySymbol,
                      exchangeRate(currencySymbol),
                      floatingPrecision
                    )
                "
                show-currency="symbol"
              />
            </td>
            <td />
          </tr>
        </template>
      </v-data-table>
    </v-card-text>
  </v-card>
</template>

<script lang="ts">
import { default as BigNumber } from 'bignumber.js';
import { Component, Prop, Vue } from 'vue-property-decorator';
import { DataTableHeader } from 'vuetify';
import { mapGetters } from 'vuex';
import { footerProps } from '@/config/datatable.common';
import { AssetBalance } from '@/store/balances/types';
import { Zero } from '@/utils/bignumbers';

@Component({
  computed: {
    ...mapGetters('session', ['floatingPrecision', 'currencySymbol']),
    ...mapGetters('balances', ['exchangeRate'])
  }
})
export default class DashboardAssetTable extends Vue {
  @Prop({ required: false, type: Boolean, default: false })
  loading!: boolean;
  @Prop({ required: true, type: String })
  title!: string;
  @Prop({ required: true, type: Array })
  balances!: AssetBalance[];

  floatingPrecision!: number;
  currencySymbol!: string;
  exchangeRate!: (currency: string) => number | undefined;

  search: string = '';

  readonly footerProps = footerProps;
  readonly headers: DataTableHeader[] = [
    {
      text: this.$tc('dashboard_asset_table.headers.asset'),
      value: 'asset'
    },
    {
      text: this.$tc('dashboard_asset_table.headers.amount'),
      value: 'amount',
      align: 'end'
    },
    {
      text: this.$tc('dashboard_asset_table.headers.value'),
      value: 'usdValue',
      align: 'end'
    },
    {
      text: this.$tc('dashboard_asset_table.headers.percentage'),
      value: 'percentage',
      align: 'end',
      sortable: false
    }
  ];

  percentage(value: BigNumber, total: BigNumber): string {
    return value.div(total).multipliedBy(100).toFixed(2);
  }

  get total(): BigNumber {
    return this.balances.reduce((sum, asset) => sum.plus(asset.usdValue), Zero);
  }
}
</script>

<style scoped lang="scss">
.dashboard-asset-table {
  &__balances {
    &__total {
      &:hover {
        background-color: transparent !important;
      }
    }
  }
}
</style>

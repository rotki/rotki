<template>
  <v-row>
    <v-col>
      <v-card>
        <v-card-title v-text="$t('tax_report_overview.title')" />
        <v-card-text>
          <v-simple-table>
            <thead>
              <tr>
                <th
                  class="text-left"
                  v-text="$t('tax_report_overview.columns.result')"
                />
                <th
                  class="text-right"
                  v-text="$t('tax_report_overview.columns.value', { symbol })"
                />
              </tr>
            </thead>
            <tbody>
              <tr v-for="(item, key) in overview" :key="key">
                <td>{{ key | splitOnCapital }}</td>
                <td class="text-right">
                  <amount-display :value="item" />
                </td>
              </tr>
            </tbody>
          </v-simple-table>
        </v-card-text>
      </v-card>
    </v-col>
  </v-row>
</template>

<script lang="ts">
import { Component, Vue } from 'vue-property-decorator';
import { mapGetters, mapState } from 'vuex';
import AmountDisplay from '@/components/display/AmountDisplay.vue';
import { Currency } from '@/model/currency';

@Component({
  components: {
    AmountDisplay
  },
  computed: {
    ...mapState('reports', ['overview']),
    ...mapGetters('session', ['currency']),
    ...mapGetters('balances', ['exchangeRate'])
  }
})
export default class TaxReportOverview extends Vue {
  overview!: TaxReportOverview;
  currency!: Currency;
  exchangeRate!: (currency: string) => number;

  get symbol(): string {
    return this.currency.ticker_symbol;
  }
}
</script>

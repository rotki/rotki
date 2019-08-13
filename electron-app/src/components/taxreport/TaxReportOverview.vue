<template>
  <v-layout>
    <v-flex>
      <v-card>
        <v-card-title>Overview</v-card-title>
        <v-card-text>
          <v-simple-table>
            <thead>
              <tr>
                <th class="text-left">Result</th>
                <th class="text-left">{{ currency.ticker_symbol }} value</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(item, key) in overview" :key="key">
                <td>{{ key | splitOnCapital }}</td>
                <td>
                  {{
                    item
                      | calculatePrice(exchangeRate(currency.ticker_symbol))
                      | formatPrice(floatingPrecision)
                  }}
                </td>
              </tr>
            </tbody>
          </v-simple-table>
        </v-card-text>
      </v-card>
    </v-flex>
  </v-layout>
</template>

<script lang="ts">
import { Component, Vue } from 'vue-property-decorator';
import { createNamespacedHelpers } from 'vuex';
import { Currency } from '@/model/currency';

const { mapState, mapGetters } = createNamespacedHelpers('session');
const mapReportsState = createNamespacedHelpers('reports').mapState;
const mapBalanceGetters = createNamespacedHelpers('balances').mapGetters;

@Component({
  computed: {
    ...mapReportsState(['overview']),
    ...mapState(['currency']),
    ...mapGetters(['floatingPrecision']),
    ...mapBalanceGetters(['exchangeRate'])
  }
})
export default class TaxReportOverview extends Vue {
  overview!: TaxReportOverview;
  currency!: Currency;
  floatingPrecision!: number;
  exchangeRate!: (currency: string) => number;
}
</script>

<style scoped></style>

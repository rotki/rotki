<template>
  <v-row>
    <v-col>
      <v-card>
        <v-card-title v-text="$t('profit_loss_overview.title')" />
        <v-card-text>
          <v-simple-table>
            <thead>
              <tr>
                <th
                  class="text-left"
                  v-text="$t('profit_loss_overview.columns.result')"
                />
                <th
                  class="text-right"
                  v-text="$t('profit_loss_overview.columns.value', { symbol })"
                />
              </tr>
            </thead>
            <tbody>
              <tr>
                <td>{{ $t('profit_loss_overview.rows.loan_profit') }}</td>
                <td class="text-right">
                  <amount-display pnl :value="overview.loanProfit" />
                </td>
              </tr>
              <tr>
                <td>{{ $t('profit_loss_overview.rows.defi_profit_loss') }}</td>
                <td class="text-right">
                  <amount-display pnl :value="overview.defiProfitLoss" />
                </td>
              </tr>
              <tr>
                <td>
                  {{ $t('profit_loss_overview.rows.margin_positions_pnl') }}
                </td>
                <td class="text-right">
                  <amount-display
                    pnl
                    :value="overview.marginPositionsProfitLoss"
                  />
                </td>
              </tr>
              <tr>
                <td>{{ $t('profit_loss_overview.rows.settlement_losses') }}</td>
                <td class="text-right">
                  <amount-display pnl :value="overview.settlementLosses" />
                </td>
              </tr>
              <tr>
                <td>
                  {{
                    $t(
                      'profit_loss_overview.rows.ethereum_transaction_gas_costs'
                    )
                  }}
                </td>
                <td class="text-right">
                  <amount-display
                    :value="overview.ethereumTransactionGasCosts"
                  />
                </td>
              </tr>
              <tr>
                <td>
                  {{ $t('profit_loss_overview.rows.asset_movement_fees') }}
                </td>
                <td class="text-right">
                  <amount-display :value="overview.assetMovementFees" />
                </td>
              </tr>
              <tr>
                <td>
                  {{
                    $t('profit_loss_overview.rows.ledger_actions_profit_loss')
                  }}
                </td>
                <td class="text-right">
                  <amount-display
                    pnl
                    :value="overview.ledgerActionsProfitLoss"
                  />
                </td>
              </tr>
              <tr>
                <td>
                  {{
                    $t('profit_loss_overview.rows.general_trade_profit_loss')
                  }}
                </td>
                <td class="text-right">
                  <amount-display
                    pnl
                    :value="overview.generalTradeProfitLoss"
                  />
                </td>
              </tr>
              <tr>
                <td>
                  {{
                    $t('profit_loss_overview.rows.taxable_trade_profit_loss')
                  }}
                </td>
                <td class="text-right subtitle-1">
                  <amount-display
                    pnl
                    :value="overview.taxableTradeProfitLoss"
                  />
                </td>
              </tr>
              <tr>
                <td colspan="2" />
              </tr>
              <tr>
                <td class="font-weight-medium subtitle-1">
                  {{ $t('profit_loss_overview.rows.total_profit_loss') }}
                </td>
                <td class="text-right subtitle-1">
                  <amount-display pnl :value="overview.totalProfitLoss" />
                </td>
              </tr>
              <tr>
                <td class="font-weight-medium subtitle-1">
                  {{
                    $t('profit_loss_overview.rows.total_taxable_profit_loss')
                  }}
                </td>
                <td class="text-right subtitle-1">
                  <amount-display
                    pnl
                    :value="overview.totalTaxableProfitLoss"
                  />
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
import { ProfitLossOverviewData } from '@/model/trade-history-types';

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
export default class ProfitLossOverview extends Vue {
  overview!: ProfitLossOverviewData;
  currency!: Currency;
  exchangeRate!: (currency: string) => number;

  get symbol(): string {
    return this.currency.ticker_symbol;
  }
}
</script>

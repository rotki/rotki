<template>
  <card outlined-body :flat="flat">
    <template #title>
      {{ $t('profit_loss_overview.title') }}
    </template>
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
            <amount-display pnl :value="overview.marginPositionsProfitLoss" />
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
            {{ $t('profit_loss_overview.rows.ethereum_transaction_gas_costs') }}
          </td>
          <td class="text-right">
            <amount-display :value="overview.ethereumTransactionGasCosts" />
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
            {{ $t('profit_loss_overview.rows.ledger_actions_profit_loss') }}
          </td>
          <td class="text-right">
            <amount-display pnl :value="overview.ledgerActionsProfitLoss" />
          </td>
        </tr>
        <tr>
          <td>
            {{ $t('profit_loss_overview.rows.general_trade_profit_loss') }}
          </td>
          <td class="text-right">
            <amount-display pnl :value="overview.generalTradeProfitLoss" />
          </td>
        </tr>
        <tr>
          <td>
            {{ $t('profit_loss_overview.rows.taxable_trade_profit_loss') }}
          </td>
          <td class="text-right text-subtitle-1">
            <amount-display pnl :value="overview.taxableTradeProfitLoss" />
          </td>
        </tr>
        <tr>
          <td colspan="2" />
        </tr>
        <tr>
          <td class="font-weight-medium text-subtitle-1">
            {{ $t('profit_loss_overview.rows.total_profit_loss') }}
          </td>
          <td class="text-right text-subtitle-1">
            <amount-display pnl :value="overview.totalProfitLoss" />
          </td>
        </tr>
        <tr>
          <td class="font-weight-medium text-subtitle-1">
            {{ $t('profit_loss_overview.rows.total_taxable_profit_loss') }}
          </td>
          <td class="text-right text-subtitle-1">
            <amount-display pnl :value="overview.totalTaxableProfitLoss" />
          </td>
        </tr>
      </tbody>
    </v-simple-table>
  </card>
</template>

<script lang="ts">
import { defineComponent, PropType } from '@vue/composition-api';
import AmountDisplay from '@/components/display/AmountDisplay.vue';
import { ProfitLossOverview } from '@/types/reports';

export default defineComponent({
  name: 'ProfitLossOverview',
  components: {
    AmountDisplay
  },
  props: {
    overview: {
      required: true,
      type: Object as PropType<ProfitLossOverview>
    },
    flat: {
      required: false,
      type: Boolean,
      default: false
    }
  }
});
</script>

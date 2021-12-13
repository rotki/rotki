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
            <amount-display
              pnl
              :value="overview.loanProfit"
              :loading="loading"
            />
          </td>
        </tr>
        <tr>
          <td>{{ $t('profit_loss_overview.rows.defi_profit_loss') }}</td>
          <td class="text-right">
            <amount-display
              pnl
              :value="overview.defiProfitLoss"
              :loading="loading"
            />
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
              :loading="loading"
            />
          </td>
        </tr>
        <tr>
          <td>{{ $t('profit_loss_overview.rows.settlement_losses') }}</td>
          <td class="text-right">
            <amount-display
              pnl
              :value="overview.settlementLosses"
              :loading="loading"
            />
          </td>
        </tr>
        <tr>
          <td>
            {{ $t('profit_loss_overview.rows.ethereum_transaction_gas_costs') }}
          </td>
          <td class="text-right">
            <amount-display
              :value="overview.ethereumTransactionGasCosts"
              :loading="loading"
            />
          </td>
        </tr>
        <tr>
          <td>
            {{ $t('profit_loss_overview.rows.asset_movement_fees') }}
          </td>
          <td class="text-right">
            <amount-display
              :value="overview.assetMovementFees"
              :loading="loading"
            />
          </td>
        </tr>
        <tr>
          <td>
            {{ $t('profit_loss_overview.rows.ledger_actions_profit_loss') }}
          </td>
          <td class="text-right">
            <amount-display
              pnl
              :value="overview.ledgerActionsProfitLoss"
              :loading="loading"
            />
          </td>
        </tr>
        <tr>
          <td>
            {{ $t('profit_loss_overview.rows.general_trade_profit_loss') }}
          </td>
          <td class="text-right">
            <amount-display
              pnl
              :value="overview.generalTradeProfitLoss"
              :loading="loading"
            />
          </td>
        </tr>
        <tr>
          <td>
            {{ $t('profit_loss_overview.rows.taxable_trade_profit_loss') }}
          </td>
          <td class="text-right text-subtitle-1">
            <amount-display
              pnl
              :value="overview.taxableTradeProfitLoss"
              :loading="loading"
            />
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
            <amount-display
              pnl
              :value="overview.totalProfitLoss"
              :loading="loading"
            />
          </td>
        </tr>
        <tr>
          <td class="font-weight-medium text-subtitle-1">
            {{ $t('profit_loss_overview.rows.total_taxable_profit_loss') }}
          </td>
          <td class="text-right text-subtitle-1">
            <amount-display
              pnl
              :value="overview.totalTaxableProfitLoss"
              :loading="loading"
            />
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
    symbol: {
      required: true,
      type: String
    },
    flat: {
      required: false,
      type: Boolean,
      default: false
    },
    loading: {
      required: false,
      type: Boolean,
      default: false
    }
  }
});
</script>

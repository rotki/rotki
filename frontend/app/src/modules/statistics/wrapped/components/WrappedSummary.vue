<script setup lang="ts">
import type { ComponentProps } from 'vue-component-type-helpers';
import type { WrapStatisticsResult } from '@/modules/statistics/api/use-wrap-statistics-api';
import WrappedExchangeCard from './cards/WrappedExchangeCard.vue';
import WrappedGasCard from './cards/WrappedGasCard.vue';
import WrappedGnosisPayCard from './cards/WrappedGnosisPayCard.vue';
import WrappedProtocolCard from './cards/WrappedProtocolCard.vue';
import WrappedTopDaysCard from './cards/WrappedTopDaysCard.vue';
import WrappedTransactionsCard from './cards/WrappedTransactionsCard.vue';
import WrappedHighlights from './WrappedHighlights.vue';

type GnosisPayCardProps = ComponentProps<typeof WrappedGnosisPayCard>;

/** The period's headline figures and the cards that break them down. */
defineProps<{
  summary: WrapStatisticsResult;
  gnosisPayResult: GnosisPayCardProps['gnosisPayResult'];
  showGnosisData: boolean;
}>();
</script>

<template>
  <WrappedHighlights
    :eth-on-gas="summary.ethOnGas"
    :transactions="summary.transactionsPerChain"
    :trades="summary.tradesByExchange"
    :top-days="summary.topDaysByNumberOfTransactions"
  />

  <div class="grid gap-4 lg:grid-cols-2">
    <WrappedTransactionsCard :transactions-per-chain="summary.transactionsPerChain" />
    <WrappedProtocolCard :transactions-per-protocol="summary.transactionsPerProtocol" />
    <WrappedGasCard :eth-on-gas-per-address="summary.ethOnGasPerAddress" />
    <WrappedTopDaysCard :top-days-by-number-of-transactions="summary.topDaysByNumberOfTransactions" />
    <WrappedExchangeCard :trades-by-exchange="summary.tradesByExchange" />
    <WrappedGnosisPayCard
      :gnosis-pay-result="gnosisPayResult"
      :show-gnosis-data="showGnosisData"
    />
  </div>
</template>

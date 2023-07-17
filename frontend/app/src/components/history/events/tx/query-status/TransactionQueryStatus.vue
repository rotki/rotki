<script setup lang="ts">
import { type Blockchain } from '@rotki/common/lib/blockchain';

const props = withDefaults(
  defineProps<{
    colspan: number;
    onlyChains?: Blockchain[];
  }>(),
  {
    onlyChains: () => []
  }
);

const { onlyChains } = toRefs(props);

const {
  sortedQueryStatus,
  getKey,
  isQueryFinished,
  resetQueryStatus,
  isAllFinished
} = useTransactionQueryStatus(onlyChains);
</script>

<template>
  <QueryStatusBar
    :colspan="colspan"
    :items="sortedQueryStatus"
    :get-key="getKey"
    :is-item-finished="isQueryFinished"
    :finished="isAllFinished"
    @reset="resetQueryStatus()"
  >
    <template #current>
      <TransactionQueryStatusCurrent :only-chains="onlyChains" />
    </template>

    <template #item="{ item }">
      <AdaptiveWrapper>
        <EvmChainIcon :chain="item.evmChain" size="20px" />
      </AdaptiveWrapper>

      <TransactionQueryStatusLine :item="item" class="ms-2" />
    </template>

    <template #dialog>
      <TransactionQueryStatusDialog :only-chains="onlyChains" />
    </template>
  </QueryStatusBar>
</template>

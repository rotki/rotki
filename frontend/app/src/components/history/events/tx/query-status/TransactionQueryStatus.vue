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
  <query-status-bar
    :colspan="colspan"
    :items="sortedQueryStatus"
    :get-key="getKey"
    :is-item-finished="isQueryFinished"
    :finished="isAllFinished"
    @reset="resetQueryStatus()"
  >
    <template #current>
      <transaction-query-status-current :only-chains="onlyChains" />
    </template>

    <template #item="{ item }">
      <adaptive-wrapper>
        <evm-chain-icon :chain="item.evmChain" size="20px" />
      </adaptive-wrapper>

      <transaction-query-status-line :item="item" class="ms-2" />
    </template>

    <template #dialog>
      <transaction-query-status-dialog :only-chains="onlyChains" />
    </template>
  </query-status-bar>
</template>

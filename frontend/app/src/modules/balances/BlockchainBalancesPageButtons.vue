<script setup lang="ts">
import BlockchainBalancesRefreshButton from '@/modules/balances/BlockchainBalancesRefreshButton.vue';
import BlockchainBalanceStalenessIndicator from '@/modules/balances/BlockchainBalanceStalenessIndicator.vue';
import HideSmallBalances from '@/modules/settings/HideSmallBalances.vue';
import { BalanceSource } from '@/modules/settings/types/frontend-settings';
</script>

<template>
  <BlockchainBalanceStalenessIndicator class="self-center" />
  <BlockchainBalancesRefreshButton />
  <HideSmallBalances :source="BalanceSource.BLOCKCHAIN" />
</template>

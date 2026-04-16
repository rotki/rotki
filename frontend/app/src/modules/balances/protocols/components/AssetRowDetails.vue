<script setup lang="ts">
import type { AssetBalanceWithPrice } from '@rotki/common';
import { isEvmNativeToken } from '@/modules/assets/types';
import AssetBalances from '@/modules/balances/AssetBalances.vue';
import EvmNativeTokenBreakdown from '@/modules/balances/EvmNativeTokenBreakdown.vue';
import AssetDetailsLayout from '@/modules/balances/protocols/components/AssetDetailsLayout.vue';
import AssetProtocolBreakdown from '@/modules/balances/protocols/components/AssetProtocolBreakdown.vue';

defineProps<{
  isLiability: boolean;
  row: AssetBalanceWithPrice;
  loading?: boolean;
  details?: {
    groupId?: string;
    chains?: string[];
  };
  allBreakdown?: boolean;
  hideBreakdown?: boolean;
}>();

function getAssets(item: AssetBalanceWithPrice): string[] {
  return item.breakdown?.map(entry => entry.asset) ?? [];
}
</script>

<template>
  <AssetDetailsLayout :row="row">
    <template #breakdown>
      <EvmNativeTokenBreakdown
        v-if="!hideBreakdown && isEvmNativeToken(row.asset)"
        :blockchain-only="!allBreakdown"
        :assets="getAssets(row)"
        :details="details"
        :identifier="row.asset"
        :is-liability="isLiability"
      />
      <AssetBalances
        v-else
        :details="details"
        :loading="loading"
        hide-total
        :hide-breakdown="hideBreakdown"
        :sticky-header="false"
        :is-liability="isLiability"
        :all-breakdown="allBreakdown"
        :visible-columns="[]"
        :show-per-protocol="false"
        :balances="row.breakdown ?? []"
      />
    </template>
    <template #perprotocol>
      <AssetProtocolBreakdown
        :data="row.perProtocol ?? []"
        :asset="row.asset"
        :loading="loading"
      />
    </template>
  </AssetDetailsLayout>
</template>

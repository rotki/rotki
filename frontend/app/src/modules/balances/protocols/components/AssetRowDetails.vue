<script setup lang="ts">
import type { AssetBalanceWithPrice } from '@rotki/common';
import AssetBalances from '@/components/AssetBalances.vue';
import EvmNativeTokenBreakdown from '@/components/EvmNativeTokenBreakdown.vue';
import AssetDetailsLayout from '@/modules/balances/protocols/components/AssetDetailsLayout.vue';
import AssetProtocolBreakdown from '@/modules/balances/protocols/components/AssetProtocolBreakdown.vue';
import { isEvmNativeToken } from '@/types/asset';

const props = withDefaults(defineProps<{
  isLiability: boolean;
  row: AssetBalanceWithPrice;
  loading?: boolean;
  details?: {
    groupId?: string;
    chains?: string[];
  };
  allBreakdown?: boolean;
  hideBreakdown?: boolean;
}>(), {
  allBreakdown: false,
  details: undefined,
  hideBreakdown: false,
  loading: false,
});

function getAssets(item: AssetBalanceWithPrice): string[] {
  return item.breakdown?.map(entry => entry.asset) ?? [];
}
</script>

<template>
  <AssetDetailsLayout :row="props.row">
    <template #breakdown>
      <EvmNativeTokenBreakdown
        v-if="!props.hideBreakdown && isEvmNativeToken(props.row.asset)"
        :blockchain-only="!props.allBreakdown"
        :assets="getAssets(props.row)"
        :details="props.details"
        :identifier="props.row.asset"
        :is-liability="props.isLiability"
      />
      <AssetBalances
        v-else
        :details="props.details"
        :loading="props.loading"
        hide-total
        :hide-breakdown="props.hideBreakdown"
        :sticky-header="false"
        :is-liability="props.isLiability"
        :all-breakdown="props.allBreakdown"
        :visible-columns="[]"
        :show-per-protocol="false"
        :balances="props.row.breakdown ?? []"
      />
    </template>
    <template #perprotocol>
      <AssetProtocolBreakdown
        :data="props.row.perProtocol ?? []"
        :asset="props.row.asset"
        :loading="props.loading"
      />
    </template>
  </AssetDetailsLayout>
</template>

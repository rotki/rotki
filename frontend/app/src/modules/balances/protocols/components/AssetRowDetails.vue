<script setup lang="ts">
import type { AssetBalanceWithPrice } from '@rotki/common';
import type { AssetBreakdownOptions } from '@/modules/balances/types/balances';
import { isEvmNativeToken } from '@/modules/assets/types';
import AssetBalances from '@/modules/balances/AssetBalances.vue';
import EvmNativeTokenBreakdown from '@/modules/balances/EvmNativeTokenBreakdown.vue';
import AssetDetailsLayout from '@/modules/balances/protocols/components/AssetDetailsLayout.vue';
import AssetProtocolBreakdown from '@/modules/balances/protocols/components/AssetProtocolBreakdown.vue';

const { breakdown } = defineProps<{
  row: AssetBalanceWithPrice;
  loading?: boolean;
  breakdown?: AssetBreakdownOptions;
}>();

const isLiability = computed<boolean>(() => breakdown?.isLiability ?? false);

const hideBreakdown = computed<boolean>(() => breakdown?.hide ?? false);

const blockchainOnly = computed<boolean>(() => !(breakdown?.all ?? false));

function getAssets(item: AssetBalanceWithPrice): string[] {
  return item.breakdown?.map(entry => entry.asset) ?? [];
}
</script>

<template>
  <AssetDetailsLayout :row="row">
    <template #breakdown>
      <EvmNativeTokenBreakdown
        v-if="!hideBreakdown && isEvmNativeToken(row.asset)"
        :blockchain-only="blockchainOnly"
        :assets="getAssets(row)"
        :details="breakdown?.scope"
        :identifier="row.asset"
        :is-liability="isLiability"
      />
      <AssetBalances
        v-else
        :loading="loading"
        hide-total
        :breakdown="breakdown"
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

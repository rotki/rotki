<script setup lang="ts">
import type { BigNumber } from '@rotki/common';
import ChainDisplay from '@/modules/accounts/blockchain/ChainDisplay.vue';
import { ValueDisplay } from '@/modules/assets/amount-display/components';
import { sortDesc } from '@/modules/core/common/data/bignumbers';
import { useSupportedChains } from '@/modules/core/common/use-supported-chains';
import WrappedCard from '../WrappedCard.vue';

const { transactionsPerChain } = defineProps<{
  transactionsPerChain?: Record<string, BigNumber>;
}>();

const { t } = useI18n({ useScope: 'global' });
const { getChain } = useSupportedChains();

const chainItems = computed<Array<[string, BigNumber]>>(() => {
  if (!transactionsPerChain)
    return [];
  return Object.entries(transactionsPerChain).sort((a, b) => sortDesc(a[1], b[1]));
});

function weight(item: [string, BigNumber]): number {
  return item[1].toNumber();
}
</script>

<template>
  <WrappedCard
    v-if="chainItems.length > 0"
    :items="chainItems"
    :weight="weight"
  >
    <template #header-icon>
      <RuiIcon
        name="lu-git-branch"
        size="16"
      />
    </template>
    <template #header>
      {{ t('wrapped.transactions_by_chain') }}
    </template>
    <template #label="{ item }">
      <ChainDisplay
        dense
        class="[&>div:first-child]:w-auto!"
        :chain="getChain(item[0].toLowerCase())"
      />
    </template>
    <template #value="{ item }">
      <ValueDisplay
        :value="item[1]"
        :format="{ integer: true }"
      />
      <span class="font-normal text-rui-text-secondary">{{ t('wrapped.unit.transactions', item[1].toNumber()) }}</span>
    </template>
  </WrappedCard>
</template>

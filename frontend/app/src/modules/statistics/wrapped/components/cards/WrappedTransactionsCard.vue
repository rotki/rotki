<script setup lang="ts">
import type { BigNumber } from '@rotki/common';
import ChainDisplay from '@/components/accounts/blockchain/ChainDisplay.vue';
import AmountDisplay from '@/components/display/amount/AmountDisplay.vue';
import { useSupportedChains } from '@/composables/info/chains';
import { sortDesc } from '@/utils/bignumbers';
import WrappedCard from '../WrappedCard.vue';

const props = defineProps<{
  transactionsPerChain?: Record<string, BigNumber>;
}>();

const { t } = useI18n({ useScope: 'global' });
const { getChain } = useSupportedChains();

const chainItems = computed<Array<[string, BigNumber]>>(() => {
  if (!props.transactionsPerChain)
    return [];
  return Object.entries(props.transactionsPerChain).sort((a, b) => sortDesc(a[1], b[1]));
});
</script>

<template>
  <WrappedCard
    v-if="chainItems.length > 0"
    :items="chainItems"
  >
    <template #header-icon>
      <RuiIcon
        name="lu-git-branch"
        class="text-rui-primary"
        size="12"
      />
    </template>
    <template #header>
      {{ t('wrapped.transactions_by_chain') }}
    </template>
    <template #label="{ item, index }">
      <span>{{ index + 1 }}.</span>
      <ChainDisplay
        dense
        class="[&>div:first-child]:!w-auto"
        :chain="getChain(item[0].toLowerCase())"
      />
    </template>
    <template #value="{ item }">
      <AmountDisplay
        :value="item[1]"
        integer
      />
      {{ t('explorers.tx') }}
    </template>
  </WrappedCard>
</template>

<script setup lang="ts">
import type { BigNumber } from '@rotki/common';
import { AssetAmountDisplay } from '@/modules/assets/amount-display/components';
import { sortDesc } from '@/modules/core/common/data/bignumbers';
import HashLink from '@/modules/shell/components/HashLink.vue';
import WrappedCard from '../WrappedCard.vue';

/** The gas each address spent; the total heads the page among the highlights. */
const { ethOnGasPerAddress } = defineProps<{
  ethOnGasPerAddress?: Record<string, BigNumber>;
}>();

const { t } = useI18n({ useScope: 'global' });
const { isSmAndDown } = useBreakpoint();

const gasPerAddressItems = computed<Array<[string, BigNumber]>>(() => {
  if (!ethOnGasPerAddress)
    return [];
  return Object.entries(ethOnGasPerAddress).sort((a, b) => sortDesc(a[1], b[1]));
});

function weight(item: [string, BigNumber]): number {
  return item[1].toNumber();
}
</script>

<template>
  <WrappedCard
    v-if="gasPerAddressItems.length > 0"
    :items="gasPerAddressItems"
    :weight="weight"
  >
    <template #header-icon>
      <RuiIcon
        name="lu-fuel"
        size="16"
      />
    </template>
    <template #header>
      {{ t('wrapped.gas_spent') }}
    </template>
    <template #label="{ item }">
      <HashLink
        :text="item[0]"
        :truncate-length="isSmAndDown ? 6 : 12"
      />
    </template>
    <template #value="{ item }">
      <AssetAmountDisplay
        asset="ETH"
        :amount="item[1]"
      />
    </template>
  </WrappedCard>
</template>

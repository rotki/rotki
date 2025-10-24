<script setup lang="ts">
import type { BigNumber } from '@rotki/common';
import AmountDisplay from '@/components/display/amount/AmountDisplay.vue';
import HashLink from '@/modules/common/links/HashLink.vue';
import { sortDesc } from '@/utils/bignumbers';
import WrappedCard from '../WrappedCard.vue';

const props = defineProps<{
  ethOnGas?: BigNumber;
  ethOnGasPerAddress?: Record<string, BigNumber>;
}>();

const { t } = useI18n({ useScope: 'global' });
const { isSmAndDown } = useBreakpoint();

const gasPerAddressItems = computed<Array<[string, BigNumber]>>(() => {
  if (!props.ethOnGasPerAddress)
    return [];
  return Object.entries(props.ethOnGasPerAddress).sort((a, b) => sortDesc(a[1], b[1]));
});
</script>

<template>
  <WrappedCard
    v-if="ethOnGas"
    :items="[{ label: t('backend_mappings.events.type.gas_fee'), value: ethOnGas }]"
  >
    <template #header-icon>
      <RuiIcon
        name="lu-fuel"
        class="text-rui-primary"
        size="12"
      />
    </template>
    <template #header>
      {{ t('wrapped.gas_spent_total') }}
    </template>
    <template #value="{ item }">
      <AmountDisplay
        :value="item.value"
        asset="ETH"
      />
    </template>
  </WrappedCard>

  <WrappedCard
    v-if="gasPerAddressItems.length > 0"
    :items="gasPerAddressItems"
  >
    <template #header-icon>
      <RuiIcon
        name="lu-fuel"
        class="text-rui-primary"
        size="12"
      />
    </template>
    <template #header>
      {{ t('wrapped.gas_spent') }}
    </template>
    <template #label="{ item }">
      <HashLink
        class="bg-rui-grey-200 dark:bg-rui-grey-800 rounded-full pr-1 pl-0"
        :text="item[0]"
        :truncate-length="isSmAndDown ? 6 : 20"
      />
    </template>
    <template #value="{ item }">
      <AmountDisplay
        :value="item[1]"
        asset="ETH"
      />
    </template>
  </WrappedCard>
</template>

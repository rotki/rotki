<script lang="ts" setup>
import type { Balance } from '@rotki/common';
import AmountDisplay from '@/components/display/amount/AmountDisplay.vue';
import ChainIcon from '@/components/helper/display/icons/ChainIcon.vue';
import { useSupportedChains } from '@/composables/info/chains';
import { useFrontendSettingsStore } from '@/store/settings/frontend';

const props = defineProps<{
  chainId: string;
  chainBalance: Balance;
  asset?: string;
  loading?: boolean;
}>();

const { chainId } = toRefs(props);

const { shouldShowAmount } = storeToRefs(useFrontendSettingsStore());
const { getChainName } = useSupportedChains();

const chainName = getChainName(chainId);
</script>

<template>
  <RuiTooltip
    :disabled="!shouldShowAmount"
    :close-delay="0"
    tooltip-class="!-ml-1"
  >
    <template #activator>
      <ChainIcon
        :chain="chainId"
        size="20px"
      />
    </template>

    <div class="flex flex-col gap-0.5">
      <div class="font-medium text-sm mb-0.5">
        {{ chainName }}
      </div>
      <AmountDisplay
        :value="chainBalance.amount"
        :asset="asset"
        :asset-padding="0.1"
        data-cy="chain-balance-amount"
      />
      <AmountDisplay
        :asset-padding="0.1"
        force-currency
        :value="chainBalance.value"
        show-currency="symbol"
        data-cy="chain-balance-value"
      />
    </div>
  </RuiTooltip>
</template>

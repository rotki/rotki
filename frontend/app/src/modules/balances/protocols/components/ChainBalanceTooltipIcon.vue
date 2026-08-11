<script lang="ts" setup>
import type { Balance } from '@rotki/common';
import { AssetAmountDisplay, FiatDisplay, ValueDisplay } from '@/modules/assets/amount-display/components';
import { useSupportedChains } from '@/modules/core/common/use-supported-chains';
import { useSetting } from '@/modules/settings/use-setting';
import ChainIcon from '@/modules/shell/components/ChainIcon.vue';

const { chainId } = defineProps<{
  chainId: string;
  chainBalance: Balance;
  asset?: string;
}>();

const shouldShowAmount = useSetting('shouldShowAmount');
const { useChainName } = useSupportedChains();

const chainName = useChainName(() => chainId);
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
      <AssetAmountDisplay
        v-if="asset"
        :asset="asset"
        :amount="chainBalance.amount"
        data-testid="chain-balance-amount"
      />
      <ValueDisplay
        v-else
        :value="chainBalance.amount"
        data-testid="chain-balance-amount"
      />
      <FiatDisplay
        :value="chainBalance.value"
        data-testid="chain-balance-value"
      />
    </div>
  </RuiTooltip>
</template>

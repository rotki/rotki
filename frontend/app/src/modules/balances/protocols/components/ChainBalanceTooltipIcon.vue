<script lang="ts" setup>
import type { Balance } from '@rotki/common';
import ChainIcon from '@/components/helper/display/icons/ChainIcon.vue';
import { useSupportedChains } from '@/composables/info/chains';
import { AssetAmountDisplay, FiatDisplay, ValueDisplay } from '@/modules/amount-display/components';
import { useFrontendSettingsStore } from '@/modules/settings/use-frontend-settings-store';

const { chainId } = defineProps<{
  chainId: string;
  chainBalance: Balance;
  asset?: string;
}>();

const { shouldShowAmount } = storeToRefs(useFrontendSettingsStore());
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
        data-cy="chain-balance-amount"
      />
      <ValueDisplay
        v-else
        :value="chainBalance.amount"
        data-cy="chain-balance-amount"
      />
      <FiatDisplay
        :value="chainBalance.value"
        data-cy="chain-balance-value"
      />
    </div>
  </RuiTooltip>
</template>

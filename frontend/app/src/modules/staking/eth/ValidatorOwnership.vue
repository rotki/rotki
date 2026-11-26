<script setup lang="ts">
import type { EthereumValidator } from '@/modules/accounts/blockchain-accounts';
import PercentageDisplay from '@/modules/shell/components/display/PercentageDisplay.vue';
import { useEthValidatorUtils } from '@/modules/staking/eth/use-eth-validator-utils';

interface Props {
  validator: EthereumValidator;
}

defineProps<Props>();

const { getOwnershipPercentage } = useEthValidatorUtils();
</script>

<template>
  <PercentageDisplay
    :value="getOwnershipPercentage(validator)"
    :asset-padding="0.1"
  />
</template>

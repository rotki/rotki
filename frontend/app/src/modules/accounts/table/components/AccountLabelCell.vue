<script setup lang="ts">
import type { BlockchainAccountBalance } from '@/modules/accounts/blockchain-accounts';
import { isXpubAccount } from '@/modules/accounts/account-utils';
import LabeledAddressDisplay from '@/modules/shell/components/display/LabeledAddressDisplay.vue';
import XpubRowSummary from './XpubRowSummary.vue';

const { row } = defineProps<{
  row: BlockchainAccountBalance;
}>();
</script>

<template>
  <LabeledAddressDisplay
    :account="row"
    class="my-2"
  />
  <XpubRowSummary
    v-if="row.type === 'group' && isXpubAccount(row)"
    :group="row"
  />
</template>

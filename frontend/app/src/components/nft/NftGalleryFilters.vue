<script setup lang="ts">
import type { AddressData, BlockchainAccount } from '@/types/blockchain/accounts';
import { Blockchain } from '@rotki/common';
import BlockchainAccountSelector from '@/components/helper/BlockchainAccountSelector.vue';
import NftCollectionSelector from '@/components/nft/NftCollectionSelector.vue';
import NftSorter from '@/components/nft/NftSorter.vue';

interface Props {
  availableAddresses: string[];
  collections: string[];
}

const selectedAccounts = defineModel<BlockchainAccount<AddressData>[]>('selectedAccounts', { required: true });

const selectedCollection = defineModel<string | undefined>('selectedCollection', { required: true });

const sortBy = defineModel<'name' | 'priceUsd' | 'collection'>('sortBy', { required: true });

const sortDescending = defineModel<boolean>('sortDescending', { required: true });

defineProps<Props>();

const { t } = useI18n({ useScope: 'global' });

const chains = [Blockchain.ETH];
</script>

<template>
  <RuiCard content-class="grid md:grid-cols-8 gap-4">
    <BlockchainAccountSelector
      v-model="selectedAccounts"
      class="md:col-span-3"
      :label="t('nft_gallery.select_account')"
      :chains="chains"
      dense
      outlined
      :usable-addresses="availableAddresses"
    />

    <NftCollectionSelector
      v-model="selectedCollection"
      class="md:col-span-3"
      :items="collections"
      variant="outlined"
      density="compact"
    />

    <NftSorter
      v-model:sort-by="sortBy"
      v-model:sort-desc="sortDescending"
      class="md:col-span-2"
    />
  </RuiCard>
</template>

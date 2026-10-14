<script setup lang="ts">
import type { AddressAccount } from '@/modules/accounts/blockchain-accounts';
import { Blockchain } from '@rotki/common';
import BlockchainAccountSelector from '@/modules/accounts/BlockchainAccountSelector.vue';
import NftCollectionSelector from '@/modules/balances/nft/NftCollectionSelector.vue';
import NftSorter from '@/modules/balances/nft/NftSorter.vue';

interface Props {
  availableAddresses: string[];
  collections: string[];
}

const selectedAccounts = defineModel<AddressAccount[]>('selectedAccounts', { required: true });

const selectedCollection = defineModel<string | undefined>('selectedCollection', { required: true });

const sortBy = defineModel<'name' | 'price' | 'collection'>('sortBy', { required: true });

const sortDescending = defineModel<boolean>('sortDescending', { required: true });

defineProps<Props>();

const { t } = useI18n({ useScope: 'global' });

const chains = [Blockchain.ETH];
</script>

<template>
  <div
    class="flex flex-wrap items-center gap-3"
    data-testid="nft-gallery-filters"
  >
    <BlockchainAccountSelector
      v-model="selectedAccounts"
      class="w-full sm:w-72"
      :source="{ chains, usableAddresses: availableAddresses }"
      :field="{ dense: true, label: t('nft_gallery.select_account') }"
      label-placement="hidden"
      :placeholder="t('nft_gallery.select_account')"
    />

    <NftCollectionSelector
      v-model="selectedCollection"
      class="w-full sm:w-64"
      :items="collections"
    />

    <NftSorter
      v-model:sort-by="sortBy"
      v-model:sort-desc="sortDescending"
      class="sm:ml-auto"
    />
  </div>
</template>

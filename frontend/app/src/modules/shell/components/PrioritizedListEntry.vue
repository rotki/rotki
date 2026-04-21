<script setup lang="ts">
import type { PrioritizedListItemData } from '@/modules/settings/types/prioritized-list-data';
import type { PrioritizedListId } from '@/modules/settings/types/prioritized-list-id';
import { toSentenceCase } from '@rotki/common';
import { AddressNamePriority } from '@/modules/accounts/address-book/types/address-name-priorities';
import { EvmIndexer } from '@/modules/settings/types/evm-indexer';
import { PriceOracle } from '@/modules/settings/types/price-oracle';
import AppImage from '@/modules/shell/components/AppImage.vue';

const { data, size = '32px' } = defineProps<{
  data: PrioritizedListItemData<PrioritizedListId>;
  size?: string;
}>();

const { t } = useI18n({ useScope: 'global' });

const labels: { [keys in PrioritizedListId]: string } = {
  [AddressNamePriority.BLOCKCHAIN_ACCOUNT]: t('address_book.hint.priority.list.blockchain_account_labels'),
  [AddressNamePriority.ENS_NAMES]: t('address_book.hint.priority.list.ens_names'),
  [AddressNamePriority.ETHEREUM_TOKENS]: t('address_book.hint.priority.list.ethereum_tokens'),
  [AddressNamePriority.GLOBAL_ADDRESSBOOK]: t('address_book.hint.priority.list.global_address_book'),
  [AddressNamePriority.HARDCODED_MAPPINGS]: t('address_book.hint.priority.list.hardcoded_mappings'),
  [AddressNamePriority.PRIVATE_ADDRESSBOOK]: t('address_book.hint.priority.list.private_address_book'),
  empty_list_id: '',
  [EvmIndexer.BLOCKSCOUT]: '',
  [EvmIndexer.ETHERSCAN]: '',
  [EvmIndexer.ROUTESCAN]: '',
  [PriceOracle.ALCHEMY]: '',
  [PriceOracle.BLOCKCHAIN]: '',
  [PriceOracle.COINGECKO]: '',
  [PriceOracle.CRYPTOCOMPARE]: '',
  [PriceOracle.DEFILLAMA]: '',
  [PriceOracle.FIAT]: '',
  [PriceOracle.MANUAL]: '',
  [PriceOracle.MANUALCURRENT]: t('oracles.manual_current'),
  [PriceOracle.UNISWAP2]: t('oracles.uniswap_v2'),
  [PriceOracle.UNISWAP3]: t('oracles.uniswap_v3'),
};
</script>

<template>
  <div class="flex items-center gap-3">
    <AppImage
      v-if="data.icon"
      :size="size"
      contain
      :src="data.icon"
      class="icon-bg"
    />
    <div v-if="labels[data.identifier]">
      {{ labels[data.identifier] }}
    </div>
    <div v-else>
      {{ toSentenceCase(data.identifier) }}
    </div>
  </div>
</template>

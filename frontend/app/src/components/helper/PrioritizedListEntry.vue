<script setup lang="ts">
import type { PrioritizedListItemData } from '@/types/settings/prioritized-list-data';
import type { PrioritizedListId } from '@/types/settings/prioritized-list-id';
import AppImage from '@/components/common/AppImage.vue';
import { AddressNamePriority } from '@/types/settings/address-name-priorities';
import { PriceOracle } from '@/types/settings/price-oracle';
import { toSentenceCase } from '@rotki/common';

const props = withDefaults(
  defineProps<{
    data: PrioritizedListItemData<PrioritizedListId>;
    size?: string;
  }>(),
  {
    size: '32px',
  },
);

const { data } = toRefs(props);

const { t } = useI18n({ useScope: 'global' });

const labels: { [keys in PrioritizedListId]: string } = {
  [AddressNamePriority.BLOCKCHAIN_ACCOUNT]: t('address_book.hint.priority.list.blockchain_account_labels'),
  [AddressNamePriority.ENS_NAMES]: t('address_book.hint.priority.list.ens_names'),
  [AddressNamePriority.ETHEREUM_TOKENS]: t('address_book.hint.priority.list.ethereum_tokens'),
  [AddressNamePriority.GLOBAL_ADDRESSBOOK]: t('address_book.hint.priority.list.global_address_book'),
  [AddressNamePriority.HARDCODED_MAPPINGS]: t('address_book.hint.priority.list.hardcoded_mappings'),
  [AddressNamePriority.PRIVATE_ADDRESSBOOK]: t('address_book.hint.priority.list.private_address_book'),
  empty_list_id: '',
  [PriceOracle.ALCHEMY]: '',
  [PriceOracle.BLOCKCHAIN]: '',
  [PriceOracle.COINGECKO]: '',
  [PriceOracle.CRYPTOCOMPARE]: '',
  [PriceOracle.DEFILLAMA]: '',
  [PriceOracle.FIAT]: '',
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

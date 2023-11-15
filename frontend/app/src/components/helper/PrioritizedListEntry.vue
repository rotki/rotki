<script setup lang="ts">
import { AddressNamePriority } from '@/types/settings/address-name-priorities';
import { PriceOracle } from '@/types/settings/price-oracle';
import { type PrioritizedListItemData } from '@/types/settings/prioritized-list-data';
import { type PrioritizedListId } from '@/types/settings/prioritized-list-id';
import { toSentenceCase } from '@/utils/text';

const props = withDefaults(
  defineProps<{
    data: PrioritizedListItemData<PrioritizedListId>;
    size?: string;
  }>(),
  {
    size: '40px'
  }
);

const { data } = toRefs(props);

const { t } = useI18n();

const labels: { [keys in PrioritizedListId]: string } = {
  [PriceOracle.UNISWAP2]: t('oracles.uniswap_v2').toString(),
  [PriceOracle.UNISWAP3]: t('oracles.uniswap_v3').toString(),
  [PriceOracle.MANUALCURRENT]: t('oracles.manual_latest').toString(),
  [AddressNamePriority.BLOCKCHAIN_ACCOUNT]: t(
    'address_book.hint.priority.list.blockchain_account_labels'
  ).toString(),
  [AddressNamePriority.ENS_NAMES]: t(
    'address_book.hint.priority.list.ens_names'
  ).toString(),
  [AddressNamePriority.ETHEREUM_TOKENS]: t(
    'address_book.hint.priority.list.ethereum_tokens'
  ).toString(),
  [AddressNamePriority.GLOBAL_ADDRESSBOOK]: t(
    'address_book.hint.priority.list.global_address_book'
  ).toString(),
  [AddressNamePriority.HARDCODED_MAPPINGS]: t(
    'address_book.hint.priority.list.hardcoded_mappings'
  ).toString(),
  [AddressNamePriority.PRIVATE_ADDRESSBOOK]: t(
    'address_book.hint.priority.list.private_address_book'
  ).toString(),
  blockchain: '',
  coingecko: '',
  cryptocompare: '',
  fiat: '',
  manual: '',
  defillama: '',
  empty_list_id: ''
};
</script>

<template>
  <div class="flex items-center gap-3">
    <AdaptiveWrapper v-if="data.icon">
      <VImg
        :width="size"
        contain
        position="left"
        :max-height="size"
        :min-height="size"
        :src="data.icon"
      />
    </AdaptiveWrapper>
    <div v-if="labels[data.identifier]">
      {{ labels[data.identifier] }}
    </div>
    <div v-else>
      {{ toSentenceCase(data.identifier) }}
    </div>
  </div>
</template>

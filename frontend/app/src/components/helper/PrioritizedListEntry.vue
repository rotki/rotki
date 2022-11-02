<template>
  <v-row align="center">
    <v-col v-if="data.icon" cols="auto">
      <adaptive-wrapper>
        <v-img
          :width="size"
          contain
          position="left"
          :max-height="size"
          :src="data.icon"
        />
      </adaptive-wrapper>
    </v-col>
    <v-col v-if="data.identifier === PriceOracle.UNISWAP2" cols="auto">
      {{ t('oracles.uniswap_v2') }}
    </v-col>
    <v-col v-else-if="data.identifier === PriceOracle.UNISWAP3" cols="auto">
      {{ t('oracles.uniswap_v3') }}
    </v-col>
    <v-col
      v-else-if="data.identifier === PriceOracle.MANUALCURRENT"
      cols="auto"
    >
      {{ t('oracles.manual_latest') }}
    </v-col>
    <v-col
      v-else-if="data.identifier === AddressNamePriority.BLOCKCHAIN_ACCOUNT"
      cols="auto"
    >
      {{ t('eth_address_book.hint.priority.list.blockchain_account_labels') }}
    </v-col>
    <v-col
      v-else-if="data.identifier === AddressNamePriority.ENS_NAMES"
      cols="auto"
    >
      {{ t('eth_address_book.hint.priority.list.ens_names') }}
    </v-col>
    <v-col
      v-else-if="data.identifier === AddressNamePriority.ETHEREUM_TOKENS"
      cols="auto"
    >
      {{ t('eth_address_book.hint.priority.list.ethereum_tokens') }}
    </v-col>
    <v-col
      v-else-if="data.identifier === AddressNamePriority.GLOBAL_ADDRESSBOOK"
      cols="auto"
    >
      {{ t('eth_address_book.hint.priority.list.global_address_book') }}
    </v-col>
    <v-col
      v-else-if="data.identifier === AddressNamePriority.HARDCODED_MAPPINGS"
      cols="auto"
    >
      {{ t('eth_address_book.hint.priority.list.hardcoded_mappings') }}
    </v-col>
    <v-col
      v-else-if="data.identifier === AddressNamePriority.PRIVATE_ADDRESSBOOK"
      cols="auto"
    >
      {{ t('eth_address_book.hint.priority.list.private_address_book') }}
    </v-col>
    <v-col v-else cols="auto">
      {{ toSentenceCase(data.identifier) }}
    </v-col>
  </v-row>
</template>

<script setup lang="ts">
import { get } from '@vueuse/core';
import { computed, toRefs } from 'vue';
import { useI18n } from 'vue-i18n-composable';
import AdaptiveWrapper from '@/components/display/AdaptiveWrapper.vue';
import { AddressNamePriority } from '@/types/address-name-priorities';
import { PriceOracle } from '@/types/price-oracle';
import { PrioritizedListItemData } from '@/types/prioritized-list-data';
import { toSentenceCase } from '@/utils/text';

const props = defineProps({
  data: { required: true, type: PrioritizedListItemData }
});

const { data } = toRefs(props);

const size = computed<string>(() => {
  let defaultSize = '48px';
  if (get(data).extraDisplaySize) {
    return get(data).extraDisplaySize ?? defaultSize;
  }
  return defaultSize;
});

const { t } = useI18n();
</script>

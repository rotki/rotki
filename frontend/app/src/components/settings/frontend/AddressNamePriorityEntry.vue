<template>
  <v-row align="center">
    <v-col cols="auto" />
    <v-col
      v-if="identifier === AddressNamePriority.BLOCKCHAIN_ACCOUNT"
      cols="auto"
    >
      {{ t('eth_address_book.hint.priority.list.blockchain_account_labels') }}
    </v-col>
    <v-col v-else-if="identifier === AddressNamePriority.ENS_NAMES" cols="auto">
      {{ t('eth_address_book.hint.priority.list.ens_names') }}
    </v-col>
    <v-col
      v-else-if="identifier === AddressNamePriority.ETHEREUM_TOKENS"
      cols="auto"
    >
      {{ t('eth_address_book.hint.priority.list.ethereum_tokens') }}
    </v-col>
    <v-col
      v-else-if="identifier === AddressNamePriority.GLOBAL_ADDRESSBOOK"
      cols="auto"
    >
      {{ t('eth_address_book.hint.priority.list.global_address_book') }}
    </v-col>
    <v-col
      v-else-if="identifier === AddressNamePriority.HARDCODED_MAPPINGS"
      cols="auto"
    >
      {{ t('eth_address_book.hint.priority.list.hardcoded_mappings') }}
    </v-col>
    <v-col
      v-else-if="identifier === AddressNamePriority.PRIVATE_ADDRESSBOOK"
      cols="auto"
    >
      {{ t('eth_address_book.hint.priority.list.private_address_book') }}
    </v-col>
    <v-col v-else cols="auto">
      {{ toSentenceCase(identifier) }}
    </v-col>
  </v-row>
</template>

<script setup lang="ts">
import { toRefs } from 'vue';
import { useI18n } from 'vue-i18n-composable';
import { AddressNamePriority } from '@/types/address-name-priorities';
import { toSentenceCase } from 'rotki/src/utils/text';

const props = defineProps({
  identifier: { required: true, type: String }
});
const { identifier } = toRefs(props);
const { t } = useI18n();
</script>

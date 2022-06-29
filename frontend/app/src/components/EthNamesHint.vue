<template>
  <v-menu offset-x nudge-right="8" max-width="400">
    <template #activator="{ on, attrs }">
      <v-icon v-bind="attrs" v-on="on"> mdi-help-circle </v-icon>
    </template>
    <div class="pa-4">
      <template v-if="withHeader">
        <div class="pb-4">
          <div>
            <b>{{ $t('eth_address_book.hint.global') }}</b>
            {{ $t('eth_address_book.hint.global_description') }}
          </div>
          <div>
            <b>{{ $t('eth_address_book.hint.private') }}</b>
            {{ $t('eth_address_book.hint.private_description') }}
          </div>
        </div>
      </template>
      <div class="d-flex align-start">
        <v-icon small class="pr-4 pt-1">mdi-information</v-icon>
        <div>
          <div>
            {{ $t('eth_address_book.hint.priority.title') }}
          </div>
          <ol class="ml-n2">
            <li v-for="(priority, index) in priorityList" :key="index">
              {{ priority }}
            </li>
          </ol>
        </div>
      </div>
    </div>
  </v-menu>
</template>
<script lang="ts">
import { defineComponent } from '@vue/composition-api';
import i18n from '@/i18n';

const priorityList = [
  i18n.t('eth_address_book.hint.priority.list.private_address_book').toString(),
  i18n
    .t('eth_address_book.hint.priority.list.blockchain_account_labels')
    .toString(),
  i18n.t('eth_address_book.hint.priority.list.global_address_book').toString(),
  i18n.t('eth_address_book.hint.priority.list.ethereum_tokens').toString(),
  i18n.t('eth_address_book.hint.priority.list.hardcoded_mappings').toString(),
  i18n.t('eth_address_book.hint.priority.list.ens_names').toString()
];

export default defineComponent({
  name: 'EthNamesHint',
  props: {
    withHeader: { required: false, type: Boolean, default: false }
  },
  setup() {
    return {
      priorityList
    };
  }
});
</script>

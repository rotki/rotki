<template>
  <blockchain-account-selector
    no-padding
    outlined
    :value="selectedAccounts"
    flat
    :label="tc('module_queried_address.label')"
    multiple
    :chains="[ETH]"
    :loading="loading"
    @input="added($event)"
  />
</template>

<script lang="ts">
import { GeneralAccount } from '@rotki/common/lib/account';
import { Blockchain } from '@rotki/common/lib/blockchain';
import {
  defineComponent,
  PropType,
  Ref,
  ref,
  toRefs,
  watch
} from '@vue/composition-api';
import { get, set } from '@vueuse/core';
import { storeToRefs } from 'pinia';
import { useI18n } from 'vue-i18n-composable';
import BlockchainAccountSelector from '@/components/helper/BlockchainAccountSelector.vue';
import { useBlockchainAccountsStore } from '@/store/balances/blockchain-accounts';
import { useQueriedAddressesStore } from '@/store/session/queried-addresses';
import { Module } from '@/types/modules';

export default defineComponent({
  components: { BlockchainAccountSelector },
  props: {
    module: { required: true, type: String as PropType<Module> }
  },
  setup(props) {
    const { module } = toRefs(props);
    const loading = ref(false);
    const selectedAccounts: Ref<GeneralAccount[]> = ref([]);
    const { tc } = useI18n();

    let store = useQueriedAddressesStore();
    const { queriedAddresses } = storeToRefs(store);
    const { addQueriedAddress, deleteQueriedAddress } = store;

    const { accounts } = storeToRefs(useBlockchainAccountsStore());

    const setSelectedAccounts = (addresses: string[]): void => {
      const selected = get(accounts).filter(account =>
        addresses.includes(account.address)
      );
      set(selectedAccounts, selected);
    };

    const added = async (accounts: GeneralAccount[]) => {
      set(loading, true);
      const selectedModule = get(module);
      const addresses = accounts.map(({ address }) => address);
      const allAddresses = get(selectedAccounts).map(({ address }) => address);
      const added = addresses.filter(
        address => !allAddresses.includes(address)
      );
      const removed = allAddresses.filter(
        address => !addresses.includes(address)
      );

      if (added.length > 0) {
        for (const address of added) {
          await addQueriedAddress({
            address,
            module: selectedModule
          });
        }
      } else if (removed.length > 0) {
        for (const address of removed) {
          await deleteQueriedAddress({
            address,
            module: selectedModule
          });
        }
      }

      setSelectedAccounts(addresses);
      set(loading, false);
    };

    watch(queriedAddresses, queried => {
      const selectedModule = get(module);
      const queriedForModule = queried[selectedModule];
      setSelectedAccounts(queriedForModule ? queriedForModule : []);
    });

    return {
      loading,
      selectedAccounts,
      ETH: Blockchain.ETH,
      added,
      tc
    };
  }
});
</script>

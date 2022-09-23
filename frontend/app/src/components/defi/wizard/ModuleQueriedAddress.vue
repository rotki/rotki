<template>
  <blockchain-account-selector
    no-padding
    outlined
    :value="selectedAccounts"
    flat
    :label="tc('common.select_address')"
    multiple
    :chains="[ETH]"
    :loading="loading"
    @input="added($event)"
  />
</template>

<script setup lang="ts">
import { GeneralAccount } from '@rotki/common/lib/account';
import { Blockchain } from '@rotki/common/lib/blockchain';
import { PropType, Ref } from 'vue';
import BlockchainAccountSelector from '@/components/helper/BlockchainAccountSelector.vue';
import { useAccountBalancesStore } from '@/store/blockchain/accountbalances';
import { useQueriedAddressesStore } from '@/store/session/queried-addresses';
import { Module } from '@/types/modules';

const props = defineProps({
  module: { required: true, type: String as PropType<Module> }
});

const { module } = toRefs(props);
const loading = ref(false);
const selectedAccounts: Ref<GeneralAccount[]> = ref([]);
const { tc } = useI18n();
const ETH = Blockchain.ETH;

let store = useQueriedAddressesStore();
const { queriedAddresses } = storeToRefs(store);
const { addQueriedAddress, deleteQueriedAddress } = store;

const { accounts } = storeToRefs(useAccountBalancesStore());

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
  const added = addresses.filter(address => !allAddresses.includes(address));
  const removed = allAddresses.filter(address => !addresses.includes(address));

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
</script>

<script setup lang="ts">
import { type GeneralAccount } from '@rotki/common/lib/account';
import { Blockchain } from '@rotki/common/lib/blockchain';

type Filter = { accounts: GeneralAccount[]; keys: string[] };

withDefaults(
  defineProps<{
    value: Filter;
    filterType?: 'address' | 'key';
  }>(),
  {
    usableAddresses: () => [],
    filterType: 'address'
  }
);

const emit = defineEmits<{
  (e: 'input', value: Filter): void;
}>();

const chain = Blockchain.ETH;
const accounts: Ref<GeneralAccount[]> = ref([]);

const { eth2Validators } = storeToRefs(useEthAccountsStore());
const { tc } = useI18n();

const input = (selection: Filter) => {
  emit('input', selection);
};

watch(accounts, accounts => {
  input({ keys: [], accounts });
});
</script>

<template>
  <blockchain-account-selector
    v-if="filterType === 'address'"
    v-model="accounts"
    no-padding
    flat
    dense
    outlined
    :chains="[chain]"
    :label="tc('eth2_validator_filter.label')"
    multiple
  />
  <validator-filter-input
    v-else
    :value="value.keys"
    :items="eth2Validators.entries"
    @input="input({ keys: $event, accounts: [] })"
  />
</template>

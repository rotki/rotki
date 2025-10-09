<script lang="ts" setup>
import type { ValidationErrors } from '@/types/api/errors';
import type { AddressData, BlockchainAccount } from '@/types/blockchain/accounts';
import type { AddTransactionHashPayload } from '@/types/history/events';
import { Blockchain, isValidTxHashOrSignature } from '@rotki/common';
import useVuelidate from '@vuelidate/core';
import { helpers, required } from '@vuelidate/validators';
import ChainSelect from '@/components/accounts/blockchain/ChainSelect.vue';
import BlockchainAccountSelector from '@/components/helper/BlockchainAccountSelector.vue';
import { useFormStateWatcher } from '@/composables/form';
import { useSupportedChains } from '@/composables/info/chains';
import { useBlockchainAccountsStore } from '@/modules/accounts/use-blockchain-accounts-store';
import { hasAccountAddress } from '@/utils/blockchain/accounts';
import { getAccountAddress } from '@/utils/blockchain/accounts/utils';
import { useRefPropVModel } from '@/utils/model';
import { toMessages } from '@/utils/validation';

const modelValue = defineModel<AddTransactionHashPayload>({ required: true });
const errors = defineModel<ValidationErrors>('errorMessages', { required: true });
const stateUpdated = defineModel<boolean>('stateUpdated', { default: false, required: false });

const { t } = useI18n({ useScope: 'global' });

const lastChain = useLocalStorage('rotki.history_event.add_by_tx_hash.chain', Blockchain.ETH);
const txHash = useRefPropVModel(modelValue, 'txHash');
const evmChain = useRefPropVModel(modelValue, 'evmChain');
const associatedAddress = useRefPropVModel(modelValue, 'associatedAddress');

const { accounts: accountsPerChain } = storeToRefs(useBlockchainAccountsStore());
const { evmAndEvmLikeTxChainsInfo, getChain } = useSupportedChains();
const txChains = useArrayMap(evmAndEvmLikeTxChainsInfo, x => x.id);

const chainOptions = computed(() => {
  const accountChains = Object.entries(get(accountsPerChain))
    .filter(([_, accounts]) => accounts.length > 0)
    .map(([chain]) => chain);

  return [...get(txChains)].filter(chain => accountChains.includes(chain));
});

const usableChains = computed<string[]>(() => {
  const evmChainVal = get(evmChain);
  if (!evmChainVal) {
    return get(chainOptions);
  }

  return [getChain(evmChainVal)];
});

watch(evmChain, (chain) => {
  if (chain) {
    set(lastChain, chain);
  }
});

onMounted(() => {
  const last = get(lastChain);
  const options = get(chainOptions);
  if (!options.includes(last) && options.length > 0) {
    set(lastChain, options[0]);
  }
  set(evmChain, get(lastChain));
});

const accounts = computed<BlockchainAccount<AddressData>[]>({
  get: () => {
    const model = get(modelValue);
    const accountFound = Object.values(get(accountsPerChain))
      .flatMap(x => x)
      .filter(hasAccountAddress)
      .find(
        item =>
          getAccountAddress(item) === model.associatedAddress
          && (!model.evmChain || model.evmChain === item.chain),
      );

    if (accountFound) {
      return [accountFound];
    }

    return [];
  },
  set: (value: BlockchainAccount<AddressData>[]) => {
    const account = value[0];
    const associatedAddress = account
      ? getAccountAddress(account)
      : '';

    set(modelValue, {
      ...get(modelValue),
      associatedAddress,
    });
  },
});

const rules = {
  associatedAddress: {
    required: helpers.withMessage(
      t('transactions.form.account.validation.non_empty'),
      (accounts: BlockchainAccount<AddressData>[]) => accounts.length > 0,
    ),
  },
  evmChain: { required },
  txHash: {
    isValidTxHashOrSignature: helpers.withMessage(t('transactions.form.tx_hash.validation.valid'), isValidTxHashOrSignature),
    required: helpers.withMessage(t('transactions.form.tx_hash.validation.non_empty'), required),
  },
};

const states = {
  associatedAddress,
  evmChain,
  txHash,
};

const v$ = useVuelidate(
  rules,
  states,
  {
    $autoDirty: true,
    $externalResults: errors,
  },
);

useFormStateWatcher(states, stateUpdated);

onBeforeUnmount(() => {
  set(errors, {});
});

defineExpose({
  validate: () => get(v$).$validate(),
});
</script>

<template>
  <div
    v-if="chainOptions.length === 0"
    class="text-rui-text-secondary"
  >
    {{ t('transactions.form.no_accounts') }}
  </div>
  <form
    v-else
    class="flex flex-col gap-4"
  >
    <div class="flex gap-2">
      <ChainSelect
        v-model="evmChain"
        class="max-w-[20rem]"
        :items="chainOptions"
        :error-messages="toMessages(v$.evmChain)"
      />
      <BlockchainAccountSelector
        v-model="accounts"
        class="flex-1"
        :chains="usableChains"
        hide-chain-icon
        outlined
        show-details
        multichain
        required
        unique
        :label="t('common.address')"
        :error-messages="toMessages(v$.associatedAddress)"
        :no-data-text="t('transactions.form.account.no_address_found')"
      />
    </div>

    <RuiTextField
      v-model="txHash"
      :label="t('common.tx_hash')"
      variant="outlined"
      color="primary"
      :error-messages="toMessages(v$.txHash)"
    />
  </form>
</template>

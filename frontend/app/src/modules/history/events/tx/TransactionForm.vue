<script lang="ts" setup>
import type { ZodType } from 'zod';
import type { AddressData, BlockchainAccount } from '@/modules/accounts/blockchain-accounts';
import type { ValidationErrors } from '@/modules/core/api/types/errors';
import type { AddTransactionHashPayload } from '@/modules/history/events/event-payloads';
import { Blockchain } from '@rotki/common';
import { hasAccountAddress } from '@/modules/accounts/account-helpers';
import { getAccountAddress } from '@/modules/accounts/account-utils';
import ChainSelect from '@/modules/accounts/blockchain/ChainSelect.vue';
import BlockchainAccountSelector from '@/modules/accounts/BlockchainAccountSelector.vue';
import { useBlockchainAccountsStore } from '@/modules/accounts/use-blockchain-accounts-store';
import { useSupportedChains } from '@/modules/core/common/use-supported-chains';
import { useModelForm } from '@/modules/core/form/use-model-form';
import { transactionFormSchema, type TransactionFormState } from '@/modules/history/events/tx/transaction-form';

const modelValue = defineModel<AddTransactionHashPayload>({ required: true });
const errors = defineModel<ValidationErrors>('errorMessages', { required: true });
const stateUpdated = defineModel<boolean>('stateUpdated', { default: false, required: false });

const { t } = useI18n({ useScope: 'global' });

const lastChain = useLocalStorage<string>('rotki.history_event.add_by_tx_hash.chain', Blockchain.ETH);

const { accounts: accountsPerChain } = storeToRefs(useBlockchainAccountsStore());
const { evmAndEvmLikeTxChainsInfo, getChain, solanaChainsData } = useSupportedChains();
const txChains = useArrayMap(evmAndEvmLikeTxChainsInfo, x => x.id);
const solanaChains = useArrayMap(solanaChainsData, x => x.id);

const chainOptions = computed<string[]>(() => {
  const accountChains = Object.entries(get(accountsPerChain))
    .filter(([_, accounts]) => accounts.length > 0)
    .map(([chain]) => chain);

  return [...get(txChains), ...get(solanaChains)].filter(chain => accountChains.includes(chain));
});

const schema = computed<ZodType>(() => transactionFormSchema({
  accountRequired: t('transactions.form.account.validation.non_empty'),
  chainRequired: t('transactions.form.chain.validation.non_empty'),
  txRefRequired: t('transactions.form.tx_hash.validation.non_empty'),
  txRefValid: t('transactions.form.tx_hash.validation.valid'),
}));

/** The dialog opens on the chain the last add used, or on the first one with an account. */
function rememberedChain(): string {
  const options = get(chainOptions);
  if (!options.includes(get<string>(lastChain)) && options.length > 0) {
    set(lastChain, options[0]);
  }
  return get<string>(lastChain);
}

const form = useModelForm<TransactionFormState>({
  model: modelValue,
  schema,
  seed: state => ({ ...state, blockchain: rememberedChain() }),
  serverErrors: errors,
  stateUpdated,
});

const usableChains = computed<string[]>(() => {
  const blockchain = form.state.blockchain;
  if (!blockchain) {
    return get(chainOptions);
  }

  return [getChain(blockchain)];
});

const accounts = computed<BlockchainAccount<AddressData>[]>({
  get: () => {
    const { associatedAddress, blockchain } = form.state;
    const accountFound = Object.values(get(accountsPerChain))
      .flatMap(x => x)
      .filter(hasAccountAddress)
      .find(
        item =>
          getAccountAddress(item) === associatedAddress
          && (!blockchain || blockchain === item.chain),
      );

    if (accountFound) {
      return [accountFound];
    }

    return [];
  },
  set: (value: BlockchainAccount<AddressData>[]) => {
    const account = value[0];
    form.state.associatedAddress = account ? getAccountAddress(account) : '';
    form.touch('associatedAddress');
  },
});

watch(() => form.state.blockchain, (chain) => {
  if (chain) {
    set(lastChain, chain);
  }
});

onBeforeUnmount(() => {
  set(errors, {});
});

defineExpose({
  validate: (): boolean => form.validate(),
});
</script>

<template>
  <div
    v-if="chainOptions.length === 0"
    class="text-rui-text-secondary"
  >
    {{ t('transactions.form.no_accounts') }}
  </div>
  <div
    v-else
    class="flex flex-col gap-4"
  >
    <div class="flex gap-2">
      <ChainSelect
        v-model="form.state.blockchain"
        class="max-w-[20rem]"
        data-testid="tx-blockchain"
        :items="chainOptions"
        :error-messages="form.errors('blockchain')"
        @update:model-value="form.touch('blockchain')"
      />
      <BlockchainAccountSelector
        v-model="accounts"
        class="flex-1"
        data-testid="tx-account"
        hide-chain-icon
        :source="{ chains: usableChains, multichain: true, unique: true }"
        :field="{
          errorMessages: form.errors('associatedAddress'),
          label: t('common.address'),
          noDataText: t('transactions.form.account.no_address_found'),
          required: true,
          showDetails: true,
        }"
      />
    </div>

    <RuiTextField
      v-model="form.state.txRef"
      data-testid="tx-ref"
      :label="`${t('common.tx_hash')} / ${t('common.signature')}`"
      variant="outlined"
      color="primary"
      :error-messages="form.errors('txRef')"
      @update:model-value="form.touch('txRef')"
    />
  </div>
</template>

<script setup lang="ts">
import { Blockchain } from '@rotki/common/lib/blockchain';
import { ApiValidationError } from '@/types/api/errors';
import type { Module } from '@/types/modules';
import type {
  BlockchainAccountPayload,
  BlockchainAccountWithBalance,
} from '@/types/blockchain/accounts';

const props = defineProps<{
  blockchain: string;
  allEvmChains: boolean;
}>();

const { blockchain, allEvmChains } = toRefs(props);

const addresses = ref<string[]>([]);
const label = ref('');
const tags = ref<string[]>([]);
const selectedModules = ref<Module[]>([]);

const errorMessages = ref<Record<string, string[]>>({});

const { addAccounts, addEvmAccounts, fetchAccounts } = useBlockchains();
const { editAccount } = useBlockchainAccounts();
const { setMessage } = useMessageStore();
const { isEvm } = useSupportedChains();
const { setSubmitFunc, accountToEdit } = useAccountDialog();
const { pending, loading } = useAccountLoading();
const { t } = useI18n();

const evmChain = isEvm(blockchain);

function reset() {
  set(addresses, []);
  set(label, '');
  set(tags, []);
  set(selectedModules, []);
}

async function save() {
  const edit = !!get(accountToEdit);
  const chain = get(blockchain);
  const isEth = chain === Blockchain.ETH;

  try {
    set(pending, true);
    const entries = get(addresses);
    if (edit) {
      const address = entries[0];
      const payload: BlockchainAccountPayload = {
        blockchain: chain,
        address,
        label: get(label),
        tags: get(tags),
      };
      await editAccount(payload);
      startPromise(fetchAccounts(chain));
    }
    else {
      const payload = entries.map(address => ({
        address,
        label: get(label),
        tags: get(tags),
      }));

      const modules = get(selectedModules);

      if (get(logicAnd(allEvmChains, isEvm(chain)))) {
        await addEvmAccounts({
          payload,
          modules,
        });
      }
      else {
        await addAccounts({
          blockchain: chain,
          payload,
          modules: isEth ? modules : undefined,
        });
      }
    }
  }
  catch (error: any) {
    let errors = error.message;

    if (error instanceof ApiValidationError)
      errors = error.getValidationErrors({});

    if (typeof errors === 'string') {
      setMessage({
        description: t('account_form.error.description', {
          error: errors,
        }).toString(),
        title: t('account_form.error.title'),
        success: false,
      });
    }
    else {
      set(errorMessages, errors);
    }

    return false;
  }
  finally {
    set(pending, false);
  }
  return true;
}

function setAccount(acc: BlockchainAccountWithBalance): void {
  set(addresses, [acc.address]);
  set(label, acc.label);
  set(tags, acc.tags);
}

watch(accountToEdit, (acc) => {
  if (!acc)
    reset();
  else
    setAccount(acc);
});

onMounted(() => {
  setSubmitFunc(save);
  const acc = get(accountToEdit);
  if (!acc)
    reset();
  else
    setAccount(acc);
});
</script>

<template>
  <div class="flex flex-col gap-6">
    <ModuleActivator
      v-if="blockchain === Blockchain.ETH && !accountToEdit"
      @update:selection="selectedModules = $event"
    />

    <slot
      v-if="evmChain && !accountToEdit"
      name="selector"
      :loading="loading"
    />

    <div class="flex flex-col gap-4">
      <AddressInput
        :addresses.sync="addresses"
        :error-messages.sync="errorMessages"
        :disabled="loading || !!accountToEdit"
        :multi="!accountToEdit"
      />
      <AccountDataInput
        :tags="tags"
        :label="label"
        :disabled="loading"
        @update:label="label = $event"
        @update:tags="tags = $event"
      />
    </div>
  </div>
</template>

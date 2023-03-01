<script setup lang="ts">
import { Blockchain } from '@rotki/common/lib/blockchain';
import { Severity } from '@rotki/common/lib/messages';
import { type Module } from '@/types/modules';
import { getMetamaskAddresses } from '@/utils/metamask';
import { type AccountPayload } from '@/types/blockchain/accounts';

const selectedModules = ref<Module[]>([]);
const label = ref('');
const tags = ref<string[]>([]);

const { notify } = useNotificationsStore();
const { tc } = useI18n();
const { isPackaged, metamaskImport } = useInterop();
const { addAccounts } = useBlockchainStore();
const { valid, setSave } = useAccountDialog();
const { loading } = useAccountLoading();

const save = async (): Promise<boolean> => {
  try {
    let addresses: string[];
    if (isPackaged) {
      addresses = await metamaskImport();
    } else {
      addresses = await getMetamaskAddresses();
    }

    const payload: AccountPayload[] = addresses.map(value => ({
      address: value,
      label: get(label),
      tags: get(tags)
    }));

    await addAccounts({
      blockchain: Blockchain.ETH,
      payload,
      modules: get(selectedModules)
    });
    return true;
  } catch (e: any) {
    const title = tc('blockchain_balances.metamask_import.error.title');
    const description = tc(
      'blockchain_balances.metamask_import.error.description',
      0,
      {
        error: e.message
      }
    );

    notify({
      title,
      message: description,
      severity: Severity.ERROR,
      display: true
    });
    return false;
  }
};

onMounted(() => {
  setSave(save);
});
</script>

<template>
  <v-form v-model="valid">
    <module-activator @update:selection="selectedModules = $event" />
    <account-data-input
      :tags="tags"
      :label="label"
      :disabled="loading"
      @update:label="label = $event"
      @update:tags="tags = $event"
    />
  </v-form>
</template>

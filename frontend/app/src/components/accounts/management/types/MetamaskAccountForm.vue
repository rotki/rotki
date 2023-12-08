<script setup lang="ts">
import { type Blockchain } from '@rotki/common/lib/blockchain';
import { Severity } from '@rotki/common/lib/messages';
import { type Module } from '@/types/modules';
import { type AccountPayload } from '@/types/blockchain/accounts';

const props = defineProps<{
  blockchain: Blockchain;
  allEvmChains: boolean;
}>();

const { blockchain, allEvmChains } = toRefs(props);

const selectedModules = ref<Module[]>([]);
const label = ref('');
const tags = ref<string[]>([]);

const { notify } = useNotificationsStore();
const { t } = useI18n();
const { isPackaged, metamaskImport } = useInterop();
const { addAccounts, addEvmAccounts } = useBlockchains();
const { setSubmitFunc, setValidation } = useAccountDialog();
const { loading } = useAccountLoading();

const save = async (): Promise<boolean> => {
  try {
    let addresses: string[];
    if (isPackaged) {
      addresses = await metamaskImport();
    } else {
      addresses = await getMetamaskAddresses();
    }

    const payload: AccountPayload[] = addresses.map(address => ({
      address,
      label: get(label),
      tags: get(tags)
    }));

    const modules = get(selectedModules);

    if (get(allEvmChains)) {
      await addEvmAccounts({
        payload,
        modules
      });
    } else {
      await addAccounts({
        blockchain: get(blockchain),
        payload,
        modules
      });
    }

    return true;
  } catch (e: any) {
    const title = t('blockchain_balances.metamask_import.error.title');
    const description = t(
      'blockchain_balances.metamask_import.error.description',
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
  setSubmitFunc(save);
  setValidation({}, {});
});
</script>

<template>
  <div class="flex flex-col gap-6">
    <ModuleActivator @update:selection="selectedModules = $event" />
    <slot name="selector" :loading="loading" />
    <div class="mt-4">
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

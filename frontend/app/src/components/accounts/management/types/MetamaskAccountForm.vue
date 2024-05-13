<script setup lang="ts">
import { Severity } from '@rotki/common/lib/messages';
import { Blockchain } from '@rotki/common/lib/blockchain';
import type { AccountManageAdd } from '@/composables/accounts/blockchain/use-account-manage';
import type { Module } from '@/types/modules';

const props = defineProps<{
  loading: boolean;
  chain: string;
}>();

const { t } = useI18n();

const { chain } = toRefs(props);
const allEvmChains = ref(true);

const selectedModules = ref<Module[]>([]);
const label = ref('');
const tags = ref<string[]>([]);

const { isPackaged, metamaskImport } = useInterop();
const { notify } = useNotificationsStore();

async function importAccounts(): Promise<AccountManageAdd | null> {
  try {
    const addresses = await (isPackaged ? metamaskImport() : getMetamaskAddresses());

    const tagData = get(tags);
    const modules = get(selectedModules);

    return {
      mode: 'add',
      type: 'account',
      chain: get(chain),
      data: addresses.map(address => ({
        address,
        tags: tagData.length > 0 ? tagData : null,
        label: get(label) || undefined,
      })),
      ...(modules.length > 0 ? { modules } : {}),
      evm: get(allEvmChains),
    };
  }
  catch (error: any) {
    logger.error(error);
    const title = t('blockchain_balances.metamask_import.error.title');
    const message = t('blockchain_balances.metamask_import.error.description', { error: error.message });

    notify({
      title,
      message,
      severity: Severity.ERROR,
      display: true,
    });
    return null;
  }
}

function onAllEvmChainsUpdate(e: boolean) {
  return set(allEvmChains, e);
}

defineExpose({
  importAccounts,
});
</script>

<template>
  <div class="flex flex-col gap-6">
    <ModuleActivator
      v-if="chain === Blockchain.ETH"
      @update:selection="selectedModules = $event"
    />
    <slot
      name="selector"
      :disabled="loading"
      :attrs="{ value: allEvmChains }"
      :on="{ input: onAllEvmChainsUpdate }"
    />
    <div class="mt-4">
      <AccountDataInput
        :tags.sync="tags"
        :label.sync="label"
        :disabled="loading"
      />
    </div>
  </div>
</template>

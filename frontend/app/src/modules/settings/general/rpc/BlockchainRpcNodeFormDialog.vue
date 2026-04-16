<script setup lang="ts">
import type { BlockchainRpcNode, BlockchainRpcNodeManageState } from '@/modules/settings/types/rpc';
import { assert, Blockchain } from '@rotki/common';
import { omit } from 'es-toolkit';
import { ApiValidationError, type ValidationErrors } from '@/modules/core/api/types/errors';
import { isBlockchain } from '@/modules/core/common/chains';
import { getErrorMessage } from '@/modules/core/common/logging/error-handling';
import { useMessageStore } from '@/modules/core/common/use-message-store';
import { useSupportedChains } from '@/modules/core/common/use-supported-chains';
import { useEvmNodesApi } from '@/modules/settings/api/use-evm-nodes-api';
import BlockchainRpcNodeForm from '@/modules/settings/general/rpc/BlockchainRpcNodeForm.vue';
import BigDialog from '@/modules/shell/components/dialogs/BigDialog.vue';

const model = defineModel<BlockchainRpcNodeManageState | undefined>({ required: true });

const emit = defineEmits<{
  complete: [];
}>();

function resetForm() {
  set(model, undefined);
}

const { t } = useI18n({ useScope: 'global' });

const errorMessages = ref<ValidationErrors>({});
const submitting = ref<boolean>(false);
const form = useTemplateRef<InstanceType<typeof BlockchainRpcNodeForm>>('form');
const stateUpdated = ref(false);

const { useChainName } = useSupportedChains();

const chain = computed<Blockchain>(() => {
  const blockchain = get(model)?.node.blockchain;
  if (!blockchain || !isBlockchain(blockchain))
    return Blockchain.ETH;

  return blockchain;
});

const chainName = useChainName(() => get(model)?.node.blockchain);

const dialogTitle = computed(() => {
  const state = get(model);
  if (state?.mode === 'edit') {
    return t('evm_rpc_node_manager.edit_dialog.title', {
      chain: get(chainName),
    });
  }
  return t('evm_rpc_node_manager.add_dialog.title', { chain: get(chainName) });
});

const api = useEvmNodesApi(chain);
const { setMessage } = useMessageStore();

async function save() {
  if (!(await get(form)?.validate()))
    return;

  const state = get(model);
  assert(state);

  const editing = state.mode === 'edit';
  const node = state.node;

  set(submitting, true);
  try {
    if (editing)
      await api.editEvmNode(node);
    else await api.addEvmNode(omit(node, ['identifier']));
    resetForm();
    emit('complete');
  }
  catch (error: unknown) {
    const chainProp = get(chainName);
    const errorTitle = editing
      ? t('evm_rpc_node_manager.edit_error.title', { chain: chainProp })
      : t('evm_rpc_node_manager.add_error.title', { chain: chainProp });

    if (error instanceof ApiValidationError) {
      const messages = error.errors;

      set(errorMessages, messages);

      const keys = Object.keys(messages);
      const formKeys: string[] = ['name', 'endpoint', 'weight', 'owned', 'active'] satisfies (keyof BlockchainRpcNode)[];
      const nodeKeys = Object.keys(node);
      const nonFormKeys = keys.filter(key => !formKeys.includes(key) && nodeKeys.includes(key));

      if (nonFormKeys.length > 0) {
        setMessage({
          description: nonFormKeys.map(key => `${key}: ${messages[key]}`).join(', '),
          success: false,
          title: errorTitle,
        });
      }
    }
    else {
      setMessage({
        description: getErrorMessage(error),
        success: false,
        title: errorTitle,
      });
    }
  }
  finally {
    set(submitting, false);
  }
}
</script>

<template>
  <BigDialog
    :display="!!modelValue"
    :title="dialogTitle"
    :primary-action="t('common.actions.save')"
    :secondary-action="t('common.actions.cancel')"
    :prompt-on-close="stateUpdated"
    :loading="submitting"
    :retain-focus="false"
    @confirm="save()"
    @cancel="resetForm()"
  >
    <BlockchainRpcNodeForm
      v-if="model"
      ref="form"
      v-model="model"
      v-model:error-messages="errorMessages"
      v-model:state-updated="stateUpdated"
    />
  </BigDialog>
</template>

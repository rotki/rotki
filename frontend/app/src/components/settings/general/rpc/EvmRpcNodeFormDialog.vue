<script setup lang="ts">
import { omit } from 'lodash-es';
import { Blockchain } from '@rotki/common/lib/blockchain';
import { ApiValidationError } from '@/types/api/errors';
import { isBlockchain } from '@/types/blockchain/chains';
import EvmRpcNodeForm from '@/components/settings/general/rpc/EvmRpcNodeForm.vue';
import type { EvmRpcNodeManageState } from '@/types/settings/rpc';

const props = defineProps<{
  value: EvmRpcNodeManageState | undefined;
}>();

const emit = defineEmits<{
  (e: 'input', value: EvmRpcNodeManageState | undefined): void;
  (e: 'complete'): void;
}>();

function resetForm() {
  emit('input', undefined);
}

const { t } = useI18n();

const model = useSimpleVModel(props, emit);
const errorMessages = ref<Record<string, string[] | string>>({});
const submitting = ref<boolean>(false);
const form = ref<InstanceType<typeof EvmRpcNodeForm>>();

const { getChainName } = useSupportedChains();

const chain = computed<Blockchain>(() => {
  const blockchain = get(model)?.node.blockchain;
  if (!blockchain || !isBlockchain(blockchain))
    return Blockchain.ETH;

  return blockchain;
});

const chainName = computed(() => {
  const chain = props.value?.node.blockchain;
  return chain ? get(getChainName(get(chain))) : '';
});

const dialogTitle = computed(() => {
  const state = get(model);
  if (state?.mode === 'edit') {
    return t('evm_rpc_node_manager.edit_dialog.title', {
      chain: state?.node.blockchain,
    });
  }
  return t('evm_rpc_node_manager.add_dialog.title', { chain: state?.node.blockchain });
});

const api = useEvmNodesApi(chain);
const { setMessage } = useMessageStore();

async function save() {
  if (!await get(form)?.validate())
    return;

  const state = get(model);
  assert(state);

  const editing = state.mode === 'edit';
  const node = state.node;

  set(submitting, true);
  try {
    if (editing)
      await api.editEvmNode(node);
    else
      await api.addEvmNode(omit(node, 'identifier'));
    resetForm();
    emit('complete');
  }
  catch (error: any) {
    const chainProp = get(chainName);
    const errorTitle = editing
      ? t('evm_rpc_node_manager.edit_error.title', { chain: chainProp })
      : t('evm_rpc_node_manager.add_error.title', { chain: chainProp });

    if (error instanceof ApiValidationError) {
      const messages = error.errors;

      set(errorMessages, messages);

      const keys = Object.keys(messages);
      const knownKeys = Object.keys(node);
      const unknownKeys = keys.filter(key => !knownKeys.includes(key));

      if (unknownKeys.length > 0) {
        setMessage({
          title: errorTitle,
          description: unknownKeys
            .map(key => `${key}: ${messages[key]}`)
            .join(', '),
          success: false,
        });
      }
    }
    else {
      setMessage({
        title: errorTitle,
        description: error.message,
        success: false,
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
    :display="!!value"
    :title="dialogTitle"
    :primary-action="t('common.actions.save')"
    :secondary-action="t('common.actions.cancel')"
    :loading="submitting"
    :retain-focus="false"
    @confirm="save()"
    @cancel="resetForm()"
  >
    <EvmRpcNodeForm
      v-if="model"
      ref="form"
      v-model="model"
      :error-messages.sync="errorMessages"
    />
  </BigDialog>
</template>

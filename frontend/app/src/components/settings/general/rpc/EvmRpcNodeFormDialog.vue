<script setup lang="ts">
import { type Blockchain } from '@rotki/common/lib/blockchain';
import { type EvmRpcNode } from '@/types/settings/rpc';

const props = defineProps<{
  value: EvmRpcNode;
  chain: Blockchain;
  chainName: string;
  isEtherscan: boolean;
  editMode: boolean;
}>();

const emit = defineEmits<{
  (e: 'input', newInput: Partial<EvmRpcNode>): void;
  (e: 'reset'): void;
}>();

const { editMode, chainName, chain } = toRefs(props);

const resetForm = () => {
  emit('reset');
};

const { openDialog, submitting, trySubmit } = useEvmRpcNodeForm(chain);

const { t } = useI18n();

const dialogTitle = computed(() => {
  if (get(editMode)) {
    return t('evm_rpc_node_manager.edit_dialog.title', {
      chain: get(chainName)
    });
  }
  return t('evm_rpc_node_manager.add_dialog.title', { chain: get(chainName) });
});
</script>

<template>
  <BigDialog
    :display="openDialog"
    :title="dialogTitle"
    :primary-action="t('common.actions.save')"
    :secondary-action="t('common.actions.cancel')"
    :loading="submitting"
    :retain-focus="false"
    @confirm="trySubmit()"
    @cancel="resetForm()"
  >
    <EvmRpcNodeForm
      :value="value"
      :chain="chain"
      :chain-name="chainName"
      :edit-mode="editMode"
      :is-etherscan="isEtherscan"
      @input="emit('input', $event)"
    />
  </BigDialog>
</template>

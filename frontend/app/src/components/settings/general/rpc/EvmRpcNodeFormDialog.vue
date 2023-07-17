<script setup lang="ts">
import { type Blockchain } from '@rotki/common/lib/blockchain';
import { type EvmRpcNode } from '@/types/settings';

defineProps<{
  value: EvmRpcNode;
  chain: Blockchain;
  isEtherscan: boolean;
  editMode: boolean;
}>();

const emit = defineEmits<{
  (e: 'input', newInput: Partial<EvmRpcNode>): void;
  (e: 'reset'): void;
}>();

const resetForm = () => {
  emit('reset');
};

const { openDialog, submitting, trySubmit } = useEvmRpcNodeForm();

const { t } = useI18n();
</script>

<template>
  <BigDialog
    :display="openDialog"
    :title="t('evm_rpc_node_manager.add_dialog.title', { chain })"
    :primary-action="t('common.actions.save')"
    :secondary-action="t('common.actions.cancel')"
    :loading="submitting"
    @confirm="trySubmit()"
    @cancel="resetForm()"
  >
    <EvmRpcNodeForm
      :value="value"
      :chain="chain"
      :edit-mode="editMode"
      :is-etherscan="isEtherscan"
      @input="emit('input', $event)"
    />
  </BigDialog>
</template>

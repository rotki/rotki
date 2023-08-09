<script setup lang="ts">
import { type Blockchain } from '@rotki/common/lib/blockchain';
import { type Validation } from '@vuelidate/core';
import { type EvmRpcNode, type EvmRpcValidation } from '@/types/settings';

const props = defineProps<{
  value: EvmRpcNode;
  chain: Blockchain;
  chainName: string;
  isEtherscan: boolean;
  editMode: boolean;
  openDialog: boolean;
  submitting: boolean;
  validation: Validation;
}>();

const emit = defineEmits<{
  (e: 'input', newInput: Partial<EvmRpcNode>): void;
  (e: 'reset'): void;
  (e: 'submit'): void;
  (e: 'update:submitfn', value: () => Promise<boolean>): void;
  (e: 'update:validation', value: EvmRpcValidation): void;
}>();

const { editMode, chainName } = toRefs(props);

const resetForm = () => {
  emit('reset');
};

const submitForm = () => {
  emit('submit');
};

const { t } = useI18n();

const dialogTitle = computed(() => {
  const chainTitle = get(chainName);
  if (get(editMode)) {
    return t('evm_rpc_node_manager.edit_dialog.title', { chain: chainTitle });
  }
  return t('evm_rpc_node_manager.add_dialog.title', { chain: chainTitle });
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
    @confirm="submitForm()"
    @cancel="resetForm()"
  >
    <EvmRpcNodeForm
      :value="value"
      :chain="chain"
      :chain-name="chainName"
      :edit-mode="editMode"
      :is-etherscan="isEtherscan"
      :validation="validation"
      @input="emit('input', $event)"
      @update:validation="emit('update:validation', $event)"
      @update:submitfn="emit('update:submitfn', $event)"
    />
  </BigDialog>
</template>

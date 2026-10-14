<script setup lang="ts">
import type { AddressAccount } from '@/modules/accounts/blockchain-accounts';
import { Blockchain } from '@rotki/common';
import { z, type ZodType } from 'zod';
import BlockchainAccountSelector from '@/modules/accounts/BlockchainAccountSelector.vue';
import { useMessageStore } from '@/modules/core/common/use-message-store';
import { requiredField } from '@/modules/core/form/fields';
import { useForm } from '@/modules/core/form/use-form';
import BigDialog from '@/modules/shell/components/dialogs/BigDialog.vue';
import { useLidoCsmApi } from '@/modules/staking/api/use-lido-csm-api';

defineOptions({
  name: 'LidoCsmAddDialog',
});

const dialogOpen = defineModel<boolean>({ required: true });

const emit = defineEmits<{
  refresh: [];
}>();

interface NodeOperatorState {
  nodeOperatorId: string;
  selectedAccount: AddressAccount[];
}

interface NodeOperatorPayload {
  address: string;
  nodeOperatorId: number;
}

const { t } = useI18n({ useScope: 'global' });

const api = useLidoCsmApi();
const { setMessage } = useMessageStore();

/**
 * Vuelidate validated the derived address string rather than the selection, so the rule is written
 * over the same value: an account whose address reads blank is still a missing address.
 */
const schema = computed<ZodType>(() => z.object({
  nodeOperatorId: requiredField(t('staking_page.lido_csm.form.validation.non_empty_id')).superRefine((value, ctx) => {
    const parsed = Number(value);
    if (!(Number.isInteger(parsed) && parsed >= 0))
      ctx.addIssue({ code: 'custom', message: t('staking_page.lido_csm.form.validation.invalid_id') });
  }),
  selectedAccount: z.array(z.custom<AddressAccount>()).superRefine((accounts, ctx) => {
    const account = accounts[0];
    if (!account || account.address.trim() === '')
      ctx.addIssue({ code: 'custom', message: t('staking_page.lido_csm.form.validation.non_empty_address') });
  }),
}));

const form = useForm<NodeOperatorState, NodeOperatorPayload>({
  initial: (): NodeOperatorState => ({ nodeOperatorId: '', selectedAccount: [] }),
  schema,
  submit: async (payload: NodeOperatorPayload): Promise<{ success: boolean }> => {
    try {
      const { message } = await api.addNodeOperator(payload);

      if (message) {
        setMessage({
          description: message,
        });
      }

      return { success: true };
    }
    catch (error: unknown) {
      setMessage({
        description: t('staking_page.lido_csm.messages.add_failed', {
          message: error instanceof Error ? error.message : String(error),
        }),
      });
      return { success: false };
    }
  },
  transform: (state): NodeOperatorPayload => {
    const account = state.selectedAccount[0];
    return {
      address: account?.address ?? '',
      nodeOperatorId: Number(state.nodeOperatorId),
    };
  },
});

const { submitting, valid } = form;

function closeDialog(): void {
  set(dialogOpen, false);
}

async function submitForm(): Promise<void> {
  if (get(submitting))
    return;

  const result = await form.submit();
  if (result.outcome !== 'success')
    return;

  closeDialog();
  emit('refresh');
}
</script>

<template>
  <BigDialog
    :display="dialogOpen"
    :title="t('staking_page.lido_csm.form.title')"
    :action="{
      disabled: !valid,
      primary: t('staking_page.lido_csm.form.submit'),
    }"
    :loading="submitting"
    :layout="{ autoHeight: true, maxWidth: '560px' }"
    data-testid="lido-csm-dialog"
    @confirm="submitForm()"
    @cancel="closeDialog()"
  >
    <div class="flex flex-col gap-4">
      <BlockchainAccountSelector
        v-model="form.state.selectedAccount"
        data-testid="lido-csm-address"
        :source="{ chains: [Blockchain.ETH] }"
        :field="{
          errorMessages: form.errors('selectedAccount'),
          hint: t('staking_page.lido_csm.form.address_hint'),
          label: t('staking_page.lido_csm.form.address_label'),
          required: true,
          showDetails: true,
        }"
        @update:model-value="form.touch('selectedAccount')"
      />
      <RuiTextField
        v-model="form.state.nodeOperatorId"
        type="number"
        min="0"
        step="1"
        color="primary"
        required
        :label="t('staking_page.lido_csm.form.node_operator_label')"
        :hint="t('staking_page.lido_csm.form.node_operator_hint')"
        :error-messages="form.errors('nodeOperatorId')"
        data-testid="lido-csm-node-operator"
        @update:model-value="form.touch('nodeOperatorId')"
      />
    </div>
  </BigDialog>
</template>

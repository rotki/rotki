<script setup lang="ts">
import type { AddressAccount } from '@/modules/accounts/blockchain-accounts';
import { Blockchain } from '@rotki/common';
import { z, type ZodType } from 'zod';
import BlockchainAccountSelector from '@/modules/accounts/BlockchainAccountSelector.vue';
import { requiredField } from '@/modules/core/form/fields';
import { toServerErrors } from '@/modules/core/form/server-errors';
import { useForm } from '@/modules/core/form/use-form';
import { useSaveFailure } from '@/modules/core/form/use-save-failure';
import BigDialog from '@/modules/shell/components/dialogs/BigDialog.vue';
import { useLidoCsmApi } from '@/modules/staking/api/use-lido-csm-api';
import { LidoCsmStakingModule } from '@/modules/staking/lido-csm/constants';
import { useLidoCsmStakingModules } from '@/modules/staking/lido-csm/use-lido-csm-staking-modules';

defineOptions({
  name: 'LidoCsmAddDialog',
});

const dialogOpen = defineModel<boolean>({ required: true });

const emit = defineEmits<{
  /** The operator was added; `warning` says what the backend could not fetch for it, if anything. */
  added: [warning?: string];
}>();

interface NodeOperatorState {
  nodeOperatorId: string;
  selectedAccount: AddressAccount[];
  stakingModuleId: LidoCsmStakingModule;
}

interface NodeOperatorPayload {
  address: string;
  nodeOperatorId: number;
  stakingModuleId: LidoCsmStakingModule;
}

const { t } = useI18n({ useScope: 'global' });

const api = useLidoCsmApi();
const { stakingModuleOptions } = useLidoCsmStakingModules();
const { capture, clear, failure, modelFieldErrors } = useSaveFailure();

/** What the backend could not fetch for an operator it did add, handed to the page once it closes. */
const addedWarning = shallowRef<string>();

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
  stakingModuleId: z.number().int(),
}));

const form = useForm<NodeOperatorState, NodeOperatorPayload>({
  initial: (): NodeOperatorState => ({ nodeOperatorId: '', selectedAccount: [], stakingModuleId: LidoCsmStakingModule.CSM }),
  schema,
  submit: async (payload: NodeOperatorPayload): Promise<{ success: boolean }> => {
    try {
      const { message } = await api.addNodeOperator(payload);
      set(addedWarning, message || undefined);
      return { success: true };
    }
    catch (error: unknown) {
      capture(error, { ...payload });
      return { success: false };
    }
  },
  transform: (state): NodeOperatorPayload => {
    const account = state.selectedAccount[0];
    return {
      address: account?.address ?? '',
      nodeOperatorId: Number(state.nodeOperatorId),
      stakingModuleId: state.stakingModuleId,
    };
  },
});

const { submitting, valid } = form;

function closeDialog(): void {
  set(dialogOpen, false);
}

/** The backend names the address field `address`; the form holds it as the picked account. */
function showFieldErrors({ address, nodeOperatorId }: Record<string, string[]>): void {
  form.setServerErrors({ nodeOperatorId: nodeOperatorId ?? [], selectedAccount: address ?? [] });
}

async function submitForm(): Promise<void> {
  if (get(submitting))
    return;

  clear();
  const result = await form.submit();
  if (result.outcome === 'error')
    showFieldErrors(toServerErrors(get(modelFieldErrors)));
  if (result.outcome !== 'success')
    return;

  closeDialog();
  emit('added', get(addedWarning));
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
    :failure="failure"
    :failure-title="t('staking_page.lido_csm.messages.add_failed')"
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
      <RuiMenuSelect
        v-model="form.state.stakingModuleId"
        :options="stakingModuleOptions"
        :label="t('staking_page.lido_csm.form.staking_module_label')"
        :hint="t('staking_page.lido_csm.form.staking_module_hint')"
        key-attr="key"
        text-attr="label"
        data-testid="lido-csm-staking-module"
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

<script setup lang="ts">
import type { AddressData, BlockchainAccount } from '@/modules/accounts/blockchain-accounts';
import { Blockchain } from '@rotki/common';
import { z, type ZodType } from 'zod';
import { getAccountAddress } from '@/modules/accounts/account-utils';
import BlockchainAccountSelector from '@/modules/accounts/BlockchainAccountSelector.vue';
import { useMessageStore } from '@/modules/core/common/use-message-store';
import { requiredField } from '@/modules/core/form/fields';
import { useForm } from '@/modules/core/form/use-form';
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
  selectedAccount: BlockchainAccount<AddressData>[];
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
  selectedAccount: z.array(z.custom<BlockchainAccount<AddressData>>()).superRefine((accounts, ctx) => {
    const account = accounts[0];
    if (!account || getAccountAddress(account).trim() === '')
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
      address: account ? getAccountAddress(account) : '',
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
  <RuiDialog
    v-model="dialogOpen"
    max-width="720"
  >
    <RuiCard
      divide
      no-padding
      :class-names="{ content: 'overflow-hidden' }"
    >
      <template #header>
        {{ t('staking_page.lido_csm.form.title') }}
      </template>
      <RuiButton
        variant="text"
        class="absolute top-2 right-2"
        icon
        @click="closeDialog()"
      >
        <RuiIcon
          class="text-white"
          name="lu-x"
        />
      </RuiButton>
      <div class="p-4 space-y-6">
        <p class="text-sm text-rui-text-secondary">
          {{ t('staking_page.lido_csm.form.description') }}
        </p>
        <div class="grid gap-4 md:grid-cols-[minmax(0,2fr)_minmax(0,1fr)]">
          <BlockchainAccountSelector
            v-model="form.state.selectedAccount"
            data-testid="lido-csm-address"
            :source="{ chains: [Blockchain.ETH] }"
            :field="{
              errorMessages: form.errors('selectedAccount'),
              hint: t('staking_page.lido_csm.form.address_hint'),
              label: t('staking_page.lido_csm.form.address_label'),
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
            :label="t('staking_page.lido_csm.form.node_operator_label')"
            :hint="t('staking_page.lido_csm.form.node_operator_hint')"
            :error-messages="form.errors('nodeOperatorId')"
            variant="outlined"
            data-testid="lido-csm-node-operator"
            @update:model-value="form.touch('nodeOperatorId')"
          />
        </div>
      </div>
      <template #footer>
        <div class="w-full flex justify-end gap-2 pt-2">
          <RuiButton
            variant="text"
            @click="closeDialog()"
          >
            {{ t('common.actions.cancel') }}
          </RuiButton>
          <RuiButton
            color="primary"
            :loading="submitting"
            :disabled="!valid"
            data-testid="lido-csm-submit"
            @click="submitForm()"
          >
            {{ t('staking_page.lido_csm.form.submit') }}
          </RuiButton>
        </div>
      </template>
    </RuiCard>
  </RuiDialog>
</template>

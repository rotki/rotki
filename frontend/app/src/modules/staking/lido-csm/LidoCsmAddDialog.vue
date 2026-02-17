<script setup lang="ts">
import type { AddressData, BlockchainAccount } from '@/types/blockchain/accounts';
import { Blockchain } from '@rotki/common';
import useVuelidate from '@vuelidate/core';
import { helpers, required } from '@vuelidate/validators';
import BlockchainAccountSelector from '@/components/helper/BlockchainAccountSelector.vue';
import { useLidoCsmApi } from '@/composables/api/staking/lido-csm';
import { useMessageStore } from '@/store/message';
import { getAccountAddress } from '@/utils/blockchain/accounts/utils';
import { toMessages } from '@/utils/validation';

defineOptions({
  name: 'LidoCsmAddDialog',
});

const dialogOpen = defineModel<boolean>({ required: true });

const emit = defineEmits<{
  refresh: [];
}>();

const { t } = useI18n({ useScope: 'global' });

const selectedAccount = ref<BlockchainAccount<AddressData>[]>([]);
const nodeOperatorId = ref<string>('');
const submitting = ref<boolean>(false);

const rules = {
  nodeOperatorId: {
    required: helpers.withMessage(
      t('staking_page.lido_csm.form.validation.non_empty_id'),
      required,
    ),
    validId: helpers.withMessage(
      t('staking_page.lido_csm.form.validation.invalid_id'),
      (value: string) => {
        const parsed = Number(value);
        return Number.isInteger(parsed) && parsed >= 0;
      },
    ),
  },
  selectedAddress: {
    required: helpers.withMessage(
      t('staking_page.lido_csm.form.validation.non_empty_address'),
      required,
    ),
  },
};

const api = useLidoCsmApi();
const { setMessage } = useMessageStore();

const selectedAddress = computed<string>(() => {
  const account = get(selectedAccount)[0];
  return account ? getAccountAddress(account) : '';
});

const v$ = useVuelidate(rules, { nodeOperatorId, selectedAddress }, { $autoDirty: true });

function closeDialog(): void {
  set(dialogOpen, false);
}

async function submitForm(): Promise<void> {
  if (!(await get(v$).$validate()) || get(submitting))
    return;

  set(submitting, true);
  try {
    const { message } = await api.addNodeOperator({
      address: get(selectedAddress),
      nodeOperatorId: Number(get(nodeOperatorId)),
    });

    if (message) {
      setMessage({
        description: message,
      });
    }

    closeDialog();
    emit('refresh');
  }
  catch (error: unknown) {
    setMessage({
      description: t('staking_page.lido_csm.messages.add_failed', {
        message: error instanceof Error ? error.message : String(error),
      }),
    });
  }
  finally {
    set(submitting, false);
  }
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
      content-class="overflow-hidden"
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
            v-model="selectedAccount"
            :chains="[Blockchain.ETH]"
            outlined
            show-details
            :label="t('staking_page.lido_csm.form.address_label')"
            :custom-hint="t('staking_page.lido_csm.form.address_hint')"
            :error-messages="toMessages(v$.selectedAddress)"
          />
          <RuiTextField
            v-model="nodeOperatorId"
            type="number"
            min="0"
            step="1"
            color="primary"
            :label="t('staking_page.lido_csm.form.node_operator_label')"
            :hint="t('staking_page.lido_csm.form.node_operator_hint')"
            :error-messages="toMessages(v$.nodeOperatorId)"
            variant="outlined"
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
            :disabled="v$.$invalid"
            @click="submitForm()"
          >
            {{ t('staking_page.lido_csm.form.submit') }}
          </RuiButton>
        </div>
      </template>
    </RuiCard>
  </RuiDialog>
</template>

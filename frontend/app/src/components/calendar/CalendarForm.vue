<script setup lang="ts">
import type { ValidationErrors } from '@/types/api/errors';
import type { AddressData, BlockchainAccount } from '@/types/blockchain/accounts';
import type { CalendarEvent } from '@/types/history/calendar';
import CalendarColorInput from '@/components/calendar/CalendarColorInput.vue';
import CalendarReminder from '@/components/calendar/CalendarReminder.vue';
import BlockchainAccountSelector from '@/components/helper/BlockchainAccountSelector.vue';
import CounterpartyInput from '@/components/inputs/CounterpartyInput.vue';
import { useFormStateWatcher } from '@/composables/form';
import { useBlockchainAccountsStore } from '@/modules/accounts/use-blockchain-accounts-store';
import { isBlockchain } from '@/types/blockchain/chains';
import { hasAccountAddress } from '@/utils/blockchain/accounts';
import { getAccountAddress } from '@/utils/blockchain/accounts/utils';
import { useRefPropVModel } from '@/utils/model';
import { toMessages } from '@/utils/validation';
import useVuelidate from '@vuelidate/core';
import { helpers, required } from '@vuelidate/validators';
import { useTemplateRef } from 'vue';

const modelValue = defineModel<CalendarEvent>({ required: true });
const errors = defineModel<ValidationErrors>('errorMessages', { required: true });
const stateUpdated = defineModel<boolean>('stateUpdated', { default: false, required: false });

defineProps<{
  editMode: boolean;
}>();

const { t } = useI18n({ useScope: 'global' });

const name = useRefPropVModel(modelValue, 'name');
const description = useRefPropVModel(modelValue, 'description');
const counterparty = useRefPropVModel(modelValue, 'counterparty');
const color = useRefPropVModel(modelValue, 'color');
const autoDelete = useRefPropVModel(modelValue, 'autoDelete');
const timestamp = useRefPropVModel(modelValue, 'timestamp');

const { accounts: accountsPerChain } = storeToRefs(useBlockchainAccountsStore());

const accounts = computed<BlockchainAccount<AddressData>[]>({
  get: () => {
    const model = get(modelValue);
    const accountFound = Object.values(get(accountsPerChain))
      .flatMap(x => x)
      .filter(hasAccountAddress)
      .find(
        item =>
          getAccountAddress(item) === model.address
          && (!model.blockchain || model.blockchain === item.chain),
      );

    if (accountFound) {
      return [accountFound];
    }

    return [];
  },
  set: (value: BlockchainAccount<AddressData>[]) => {
    const account = value[0];
    const address = account ? getAccountAddress(account) : undefined;
    const blockchain = account && isBlockchain(account.chain) ? account.chain : undefined;

    set(modelValue, {
      ...get(modelValue),
      address,
      blockchain,
    });
  },
});

const reminderRef = useTemplateRef<InstanceType<typeof CalendarReminder>>('reminderRef');

const externalServerValidation = () => true;

const rules = {
  accounts: { externalServerValidation },
  autoDelete: { externalServerValidation },
  counterparty: { externalServerValidation },
  description: { externalServerValidation },
  name: {
    required: helpers.withMessage(t('calendar.form.name.validation.non_empty'), required),
  },
  timestamp: { externalServerValidation },
};

const states = {
  accounts,
  autoDelete,
  counterparty,
  description,
  name,
  timestamp,
};

const v$ = useVuelidate(
  rules,
  states,
  {
    $autoDirty: true,
    $externalResults: errors,
  },
);

useFormStateWatcher(states, stateUpdated);

defineExpose({
  reset: () => get(v$).$reset(),
  saveTemporaryReminder: (eventId: number) => get(reminderRef)?.saveTemporaryReminder(eventId),
  validate: () => get(v$).$validate(),
});
</script>

<template>
  <div class="flex flex-col gap-4">
    <div>
      <RuiDateTimePicker
        v-model="timestamp"
        :label="t('common.datetime')"
        persistent-hint
        color="primary"
        variant="outlined"
        data-cy="datetime"
        type="epoch"
        :error-messages="toMessages(v$.timestamp)"
        @blur="v$.timestamp.$touch()"
      />

      <CalendarReminder
        ref="reminderRef"
        v-model="modelValue"
        :edit-mode="editMode"
        class="pt-2"
      />
    </div>

    <div class="flex gap-4 pt-4">
      <RuiTextField
        v-model="name"
        class="flex-1"
        :label="t('common.name')"
        variant="outlined"
        color="primary"
        :error-messages="toMessages(v$.name)"
        @blur="v$.name.$touch()"
      />

      <div class="pt-3">
        <CalendarColorInput v-model="color" />
      </div>
    </div>

    <RuiTextArea
      v-model="description"
      :label="t('common.description')"
      variant="outlined"
      color="primary"
      min-rows="5"
      :error-messages="toMessages(v$.description)"
      :hint="t('common.optional')"
      @blur="v$.description.$touch()"
    />

    <BlockchainAccountSelector
      v-model="accounts"
      outlined
      :label="t('common.account')"
      :error-messages="toMessages(v$.accounts)"
      show-details
      :custom-hint="t('common.optional')"
    />

    <CounterpartyInput
      v-model="counterparty"
      :label="t('common.counterparty')"
      data-cy="counterparty"
      :error-messages="toMessages(v$.counterparty)"
      :hint="t('common.optional')"
      persistent-hint
      @blur="v$.counterparty.$touch()"
    />

    <RuiCheckbox
      v-model="autoDelete"
      :label="t('calendar.dialog.settings.auto_delete_entry')"
      color="primary"
      hide-details
    />
  </div>
</template>

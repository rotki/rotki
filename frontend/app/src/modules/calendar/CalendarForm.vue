<script setup lang="ts">
import type { ZodType } from 'zod';
import type { AddressAccount } from '@/modules/accounts/blockchain-accounts';
import type { CalendarEvent } from '@/modules/calendar/types';
import type { ValidationErrors } from '@/modules/core/api/types/errors';
import { useTemplateRef } from 'vue';
import { isAddressAccount } from '@/modules/accounts/account-utils';
import BlockchainAccountSelector from '@/modules/accounts/BlockchainAccountSelector.vue';
import { useBlockchainAccountsStore } from '@/modules/accounts/use-blockchain-accounts-store';
import CalendarColorInput from '@/modules/calendar/CalendarColorInput.vue';
import CalendarReminder from '@/modules/calendar/CalendarReminder.vue';
import { calendarEventSchema } from '@/modules/calendar/event-forms';
import { isBlockchain } from '@/modules/core/common/chains';
import { useModelForm } from '@/modules/core/form/use-model-form';
import CounterpartyInput from '@/modules/history/events/mapping/CounterpartyInput.vue';
import DateTimePicker from '@/modules/shell/components/inputs/DateTimePicker.vue';

const modelValue = defineModel<CalendarEvent>({ required: true });
const errors = defineModel<ValidationErrors>('errorMessages', { required: true });
const stateUpdated = defineModel<boolean>('stateUpdated', { default: false, required: false });

defineProps<{
  editMode: boolean;
}>();

const { t } = useI18n({ useScope: 'global' });

const { accounts: accountsPerChain } = storeToRefs(useBlockchainAccountsStore());

const reminderRef = useTemplateRef<InstanceType<typeof CalendarReminder>>('reminderRef');

const schema = computed<ZodType>(() => calendarEventSchema({
  name: t('calendar.form.name.validation.non_empty'),
}));

const form = useModelForm<CalendarEvent>({
  model: modelValue,
  schema,
  serverErrors: errors,
  stateUpdated,
  // Carried on the event but not edited here, so they must not arm the unsaved-changes prompt.
  transientKeys: ['identifier', 'color'],
});

/**
 * The selector works in accounts while the event stores an address and a chain, so this is a view
 * over two state fields rather than a field of its own.
 */
const accounts = computed<AddressAccount[]>({
  get: () => {
    const found = Object.values(get(accountsPerChain))
      .flatMap(x => x)
      .filter(isAddressAccount)
      .find(item =>
        item.address === form.state.address
        && (!form.state.blockchain || form.state.blockchain === item.chain));

    return found ? [found] : [];
  },
  set: (value: AddressAccount[]) => {
    const account = value[0];
    form.state.address = account?.address;
    form.state.blockchain = account && isBlockchain(account.chain) ? account.chain : undefined;
  },
});

defineExpose({
  reset: (): void => {
    form.reset();
  },
  saveReminders: async (eventId: number): Promise<void> => get(reminderRef)?.save(eventId),
  /** Gates on both forms: the reminder rows are their own, so their validity is combined here. */
  validate: (): boolean => {
    const event = form.validate();
    const reminders = get(reminderRef)?.validate() ?? true;
    return event && reminders;
  },
});
</script>

<template>
  <div class="flex flex-col gap-2">
    <RuiTextField
      v-model="form.state.name"
      :label="t('common.name')"
      color="primary"
      :error-messages="form.errors('name')"
      data-testid="calendar-form-name"
      @blur="form.touch('name')"
    >
      <template #prepend>
        <CalendarColorInput v-model="form.state.color" />
      </template>
    </RuiTextField>

    <DateTimePicker
      v-model="form.state.timestamp"
      :label="t('common.datetime')"
      data-testid="datetime"
      type="epoch"
      :error-messages="form.errors('timestamp')"
      @blur="form.touch('timestamp')"
    />

    <RuiTextArea
      :model-value="form.state.description ?? ''"
      :label="t('common.description')"
      color="primary"
      min-rows="3"
      :error-messages="form.errors('description')"
      :hint="t('common.optional')"
      data-testid="calendar-form-description"
      @update:model-value="form.state.description = $event"
      @blur="form.touch('description')"
    />

    <div class="grid gap-x-4 gap-y-2 md:grid-cols-2">
      <BlockchainAccountSelector
        v-model="accounts"
        :field="{
          errorMessages: form.errors('address'),
          hint: t('common.optional'),
          label: t('common.account'),
          showDetails: true,
        }"
      />

      <CounterpartyInput
        v-model="form.state.counterparty"
        :label="t('common.counterparty')"
        data-testid="counterparty"
        :error-messages="form.errors('counterparty')"
        :hint="t('common.optional')"
        persistent-hint
        @blur="form.touch('counterparty')"
      />
    </div>

    <CalendarReminder
      ref="reminderRef"
      v-model="modelValue"
      :edit-mode="editMode"
    />

    <RuiCheckbox
      v-model="form.state.autoDelete"
      :label="t('calendar.dialog.settings.auto_delete_entry')"
      color="primary"
      hide-details
    />
  </div>
</template>

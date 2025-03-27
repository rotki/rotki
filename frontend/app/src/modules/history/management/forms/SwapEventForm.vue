<script setup lang="ts">
import type { ValidationErrors } from '@/types/api/errors';
import type { AddSwapEventPayload, EventData, SwapEvent } from '@/types/history/events';
import LocationSelector from '@/components/helper/LocationSelector.vue';
import AmountInput from '@/components/inputs/AmountInput.vue';
import AssetSelect from '@/components/inputs/AssetSelect.vue';
import DateTimePicker from '@/components/inputs/DateTimePicker.vue';
import { useFormStateWatcher } from '@/composables/form';
import { useHistoryEvents } from '@/composables/history/events';
import { useMessageStore } from '@/store/message';
import { DateFormat } from '@/types/date-format';
import { convertFromTimestamp, convertToTimestamp } from '@/utils/date';
import { toMessages } from '@/utils/validation';
import { assert, HistoryEventEntryType } from '@rotki/common';
import useVuelidate from '@vuelidate/core';
import { helpers, required } from '@vuelidate/validators';
import dayjs from 'dayjs';
import { omit, pick } from 'es-toolkit';
import { isEmpty } from 'es-toolkit/compat';

type FormData = Required<AddSwapEventPayload>;

const stateUpdated = defineModel<boolean>('stateUpdated', { default: false, required: false });

const props = defineProps<{ data: EventData<SwapEvent> }>();

function emptyEvent(): FormData {
  return {
    entryType: HistoryEventEntryType.SWAP_EVENT,
    feeAmount: '',
    feeAsset: '',
    location: '',
    notes: ['', '', ''],
    receiveAmount: '0',
    receiveAsset: '',
    spendAmount: '0',
    spendAsset: '',
    timestamp: dayjs().valueOf(),
    uniqueId: '',
  };
}

const states = ref<FormData>(emptyEvent());
const hasFee = ref<boolean>(false);
const identifiers = ref<{ eventIdentifier: string; identifier: number }>();
const errorMessages = ref<Record<string, string[]>>({});

const datetime = computed<string>({
  get() {
    return convertFromTimestamp(get(states, 'timestamp'), DateFormat.DateMonthYearHourMinuteSecond, true);
  },
  set(value?: string) {
    const timestamp = !value
      ? dayjs().valueOf()
      : convertToTimestamp(value, DateFormat.DateMonthYearHourMinuteSecond, true);
    set(states, { ...get(states), timestamp });
  },
});

const externalServerValidation = () => true;

const { t } = useI18n({ useScope: 'global' });

const rules = {
  feeAmount: { externalServerValidation },
  feeAsset: { externalServerValidation },
  location: {
    required: helpers.withMessage(t('transactions.events.form.location.validation.non_empty'), required),
  },
  notes: { externalServerValidation },
  receiveAmount: {
    required: helpers.withMessage(t('transactions.events.form.amount.validation.non_empty'), required),
  },
  receiveAsset: {
    required: helpers.withMessage(t('transactions.events.form.asset.validation.non_empty'), required),
  },
  spendAmount: {
    required: helpers.withMessage(t('transactions.events.form.amount.validation.non_empty'), required),
  },
  spendAsset: {
    required: helpers.withMessage(t('transactions.events.form.asset.validation.non_empty'), required),
  },
  timestamp: { externalServerValidation },
  uniqueId: { externalServerValidation },
};

const v$ = useVuelidate(
  rules,
  states,
  {
    $autoDirty: true,
    $externalResults: errorMessages,
  },
);

useFormStateWatcher(states, stateUpdated);
const { setMessage } = useMessageStore();
const { addHistoryEvent, editHistoryEvent } = useHistoryEvents();

function handleValidationErrors(message: ValidationErrors | string) {
  if (typeof message === 'string') {
    setMessage({
      description: message,
    });
  }
  else {
    set(errorMessages, message);
  }
}

async function save(): Promise<boolean> {
  if (!(await get(v$).$validate())) {
    return false;
  }

  const model = get(states);
  let payload: AddSwapEventPayload;
  if (get(hasFee)) {
    payload = model;
  }
  else {
    payload = omit(model, ['feeAmount', 'feeAsset']);
    payload.notes = [model.notes[0], model.notes[1]];
  }

  const result = isDefined(identifiers)
    ? await editHistoryEvent({
      ...omit(payload, ['uniqueId']),
      ...get(identifiers),
    })
    : await addHistoryEvent(payload);

  if (result.success) {
    set(states, emptyEvent());
    set(identifiers, undefined);
    set(hasFee, false);
  }
  else {
    const message = result.message;
    if (message) {
      handleValidationErrors(message);
    }
  }

  return result.success;
}

function getNotes(event?: SwapEvent): string {
  if (!event || !event.notes || 'defaultNotes' in event) {
    return '';
  }
  return event.notes;
}

watchImmediate(() => props.data, (data) => {
  if (data.type !== 'edit')
    return;

  const spend = data.eventsInGroup.find(item => item.eventSubtype === 'spend');
  const receive = data.eventsInGroup.find(item => item.eventSubtype === 'receive');
  const fee = data.eventsInGroup.find(item => item.eventSubtype === 'fee');

  assert(spend);
  assert(receive);

  set(hasFee, fee !== undefined);
  set(identifiers, pick(spend, ['eventIdentifier', 'identifier']));

  const notes: [string, string, string] | [string, string] = fee !== undefined
    ? [
        getNotes(spend),
        getNotes(receive),
        getNotes(fee),
      ]
    : [
        getNotes(spend),
        getNotes(receive),
      ];
  set(states, {
    entryType: HistoryEventEntryType.SWAP_EVENT,
    feeAmount: fee?.amount?.toString() ?? '',
    feeAsset: fee?.asset ?? '',
    location: spend.location,
    notes,
    receiveAmount: receive.amount.toString(),
    receiveAsset: receive.asset,
    spendAmount: spend.amount.toString(),
    spendAsset: spend.asset,
    timestamp: spend.timestamp,
    uniqueId: '',
  });
});

watch(hasFee, (hasFee) => {
  if (hasFee) {
    return;
  }
  const oldStates = get(states);
  set(states, {
    ...oldStates,
    feeAmount: '',
    feeAsset: '',
    notes: [oldStates.notes[0], oldStates.notes[1]],
  });
});

watch(errorMessages, (errors) => {
  if (!isEmpty(errors))
    get(v$).$validate();
});

defineExpose({
  save,
});
</script>

<template>
  <div>
    <div class="grid md:grid-cols-2 gap-4 mb-4">
      <DateTimePicker
        v-model="datetime"
        :label="t('common.datetime')"
        persistent-hint
        limit-now
        milliseconds
        data-cy="datetime"
        :hint="t('transactions.events.form.datetime.hint')"
        :error-messages="toMessages(v$.timestamp)"
        @blur="v$.timestamp.$touch()"
      />
      <LocationSelector
        v-model="states.location"
        :disabled="data.type !== 'add'"
        data-cy="location"
        :label="t('common.location')"
        :error-messages="toMessages(v$.location)"
        @blur="v$.location.$touch()"
      />
    </div>

    <RuiDivider class="mb-6 mt-2" />

    <div class="grid md:grid-cols-2 gap-4">
      <AmountInput
        v-model="states.spendAmount"
        clearable
        variant="outlined"
        data-cy="spend-amount"
        :label="t('swap_event_form.spend_amount')"
        :error-messages="toMessages(v$.spendAmount)"
      />
      <AssetSelect
        v-model="states.spendAsset"
        outlined
        clearable
        data-cy="spend-asset"
        :label="t('swap_event_form.spend_asset')"
        :error-messages="toMessages(v$.spendAsset)"
      />
    </div>

    <div class="grid md:grid-cols-2 gap-4">
      <AmountInput
        v-model="states.receiveAmount"
        clearable
        variant="outlined"
        data-cy="received-amount"
        :label="t('swap_event_form.receive_amount')"
        :error-messages="toMessages(v$.receiveAmount)"
      />
      <AssetSelect
        v-model="states.receiveAsset"
        outlined
        clearable
        data-cy="received-asset"
        :label="t('swap_event_form.receive_asset')"
        :error-messages="toMessages(v$.receiveAsset)"
      />
    </div>

    <RuiTextField
      v-if="data.type !== 'edit'"
      v-model="states.uniqueId"
      variant="outlined"
      color="primary"
      data-cy="unique-id"
      :hint="t('swap_event_form.unique_id_hint')"
      :label="t('swap_event_form.unique_id')"
      :error-messages="toMessages(v$.uniqueId)"
    />

    <RuiDivider class="mb-6 mt-2" />

    <RuiCheckbox
      v-model="hasFee"
      label="Has Fee"
      data-cy="has-fee"
      color="primary"
    />

    <div class="grid md:grid-cols-2 gap-4">
      <AmountInput
        v-model="states.feeAmount"
        clearable
        :disabled="!hasFee"
        variant="outlined"
        data-cy="fee-amount"
        :label="t('common.fee')"
        :error-messages="toMessages(v$.feeAmount)"
      />
      <AssetSelect
        v-model="states.feeAsset"
        outlined
        :disabled="!hasFee"
        clearable
        data-cy="fee-asset"
        :label="t('transactions.events.form.fee_asset.label')"
        :error-messages="toMessages(v$.feeAsset)"
      />
    </div>

    <RuiAccordions>
      <RuiAccordion
        data-cy="advanced-accordion"
        header-class="py-4"
        eager
      >
        <template #header>
          {{ t('transactions.events.form.advanced') }}
        </template>

        <div class="py-2">
          <RuiTextArea
            v-model="states.notes[0]"
            prepend-icon="lu-sticky-note"
            data-cy="spend-notes"
            variant="outlined"
            color="primary"
            max-rows="5"
            min-rows="3"
            auto-grow
            :label="t('swap_event_form.spend_notes')"
            :error-messages="toMessages(v$.notes)"
            @blur="v$.notes.$touch()"
          />
          <RuiTextArea
            v-model="states.notes[1]"
            prepend-icon="lu-sticky-note"
            data-cy="receive-notes"
            variant="outlined"
            color="primary"
            max-rows="5"
            min-rows="3"
            auto-grow
            :label="t('swap_event_form.receive_notes')"
            :error-messages="toMessages(v$.notes)"
            @blur="v$.notes.$touch()"
          />
          <RuiTextArea
            v-if="hasFee && states.notes.length === 3"
            v-model="states.notes[2]"
            prepend-icon="lu-sticky-note"
            data-cy="fee-notes"
            :disabled="!hasFee"
            variant="outlined"
            color="primary"
            max-rows="5"
            min-rows="3"
            auto-grow
            :label="t('swap_event_form.fee_notes')"
            :error-messages="toMessages(v$.notes)"
            @blur="v$.notes.$touch()"
          />
        </div>
      </RuiAccordion>
    </RuiAccordions>
  </div>
</template>

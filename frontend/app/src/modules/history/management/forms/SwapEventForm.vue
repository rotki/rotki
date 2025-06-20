<script setup lang="ts">
import type { GroupEventData } from '@/modules/history/management/forms/form-types';
import type { ValidationErrors } from '@/types/api/errors';
import type { AddSwapEventPayload, SwapEvent } from '@/types/history/events';
import { useFormStateWatcher } from '@/composables/form';
import { useHistoryEvents } from '@/composables/history/events';
import { useEditModeStateTracker } from '@/composables/history/events/edit-mode-state';
import EventDateLocation from '@/modules/history/management/forms/common/EventDateLocation.vue';
import SwapEventAssetAmount from '@/modules/history/management/forms/swap/SwapEventAssetAmount.vue';
import SwapEventFee from '@/modules/history/management/forms/swap/SwapEventFee.vue';
import SwapEventNotes from '@/modules/history/management/forms/swap/SwapEventNotes.vue';
import { useEventFormValidation } from '@/modules/history/management/forms/use-event-form-validation';
import { useDateTime } from '@/modules/history/management/forms/utils';
import { useMessageStore } from '@/store/message';
import { toMessages } from '@/utils/validation';
import { assert, HistoryEventEntryType } from '@rotki/common';
import useVuelidate from '@vuelidate/core';
import dayjs from 'dayjs';
import { omit, pick } from 'es-toolkit';
import { isEmpty } from 'es-toolkit/compat';

type FormData = Required<AddSwapEventPayload>;

const stateUpdated = defineModel<boolean>('stateUpdated', { default: false, required: false });

const props = defineProps<{ data: GroupEventData<SwapEvent> }>();

function emptyEvent(): FormData {
  return {
    entryType: HistoryEventEntryType.SWAP_EVENT,
    feeAmount: '',
    feeAsset: '',
    location: '',
    receiveAmount: '0',
    receiveAsset: '',
    spendAmount: '0',
    spendAsset: '',
    timestamp: dayjs().valueOf(),
    uniqueId: '',
    userNotes: ['', '', ''],
  };
}

const states = ref<FormData>(emptyEvent());
const hasFee = ref<boolean>(false);
const identifiers = ref<{ eventIdentifier: string; identifier: number }>();
const errorMessages = ref<Record<string, string[]>>({});

const datetime = useDateTime(states);

const { t } = useI18n({ useScope: 'global' });

const { createCommonRules } = useEventFormValidation();
const commonRules = createCommonRules();

const rules = {
  feeAmount: commonRules.createExternalValidationRule(),
  feeAsset: commonRules.createExternalValidationRule(),
  location: commonRules.createRequiredLocationRule(),
  receiveAmount: commonRules.createRequiredAmountRule(),
  receiveAsset: commonRules.createRequiredAssetRule(),
  spendAmount: commonRules.createRequiredAmountRule(),
  spendAsset: commonRules.createRequiredAssetRule(),
  timestamp: commonRules.createExternalValidationRule(),
  uniqueId: commonRules.createExternalValidationRule(),
  userNotes: commonRules.createExternalValidationRule(),
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
const { captureEditModeState, shouldSkipSave } = useEditModeStateTracker();

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

  const isEditMode = isDefined(identifiers);

  if (shouldSkipSave(isEditMode, get(states))) {
    return true;
  }

  const model = get(states);
  let payload: AddSwapEventPayload;
  if (get(hasFee)) {
    payload = model;
  }
  else {
    payload = omit(model, ['feeAmount', 'feeAsset']);
    payload.userNotes = [model.userNotes[0], model.userNotes[1]];
  }

  const result = isEditMode
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
  if (!event || !event.userNotes) {
    return '';
  }
  return event.userNotes;
}

watchImmediate(() => props.data, (data) => {
  if (data.type !== 'edit-group')
    return;

  const spend = data.eventsInGroup.find(item => item.eventSubtype === 'spend');
  const receive = data.eventsInGroup.find(item => item.eventSubtype === 'receive');
  const fee = data.eventsInGroup.find(item => item.eventSubtype === 'fee');

  assert(spend);
  assert(receive);

  set(hasFee, fee !== undefined);
  set(identifiers, pick(spend, ['eventIdentifier', 'identifier']));

  const userNotes: [string, string, string] | [string, string] = fee !== undefined
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
    receiveAmount: receive.amount.toString(),
    receiveAsset: receive.asset,
    spendAmount: spend.amount.toString(),
    spendAsset: spend.asset,
    timestamp: spend.timestamp,
    uniqueId: '',
    userNotes,
  });

  captureEditModeState(get(states));
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
    userNotes: [oldStates.userNotes[0], oldStates.userNotes[1]],
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
    <EventDateLocation
      v-model:datetime="datetime"
      v-model:location="states.location"
      :location-disabled="data.type !== 'add'"
      :error-messages="{
        location: toMessages(v$.location),
        datetime: toMessages(v$.timestamp),
      }"
      @blur="v$[$event].$touch()"
    />

    <RuiDivider class="mb-6 mt-2" />

    <SwapEventAssetAmount
      v-model:asset="states.spendAsset"
      v-model:amount="states.spendAmount"
      :location="states.location"
      type="spend"
      :error-messages="{
        asset: toMessages(v$.spendAsset),
        amount: toMessages(v$.spendAmount),
      }"
    />

    <SwapEventAssetAmount
      v-model:asset="states.receiveAsset"
      v-model:amount="states.receiveAmount"
      :location="states.location"
      type="receive"
      :error-messages="{
        asset: toMessages(v$.receiveAsset),
        amount: toMessages(v$.receiveAmount),
      }"
    />

    <RuiTextField
      v-if="data.type !== 'edit-group'"
      v-model="states.uniqueId"
      variant="outlined"
      color="primary"
      data-cy="unique-id"
      :hint="t('swap_event_form.unique_id_hint')"
      :label="t('swap_event_form.unique_id')"
      :error-messages="toMessages(v$.uniqueId)"
    />

    <RuiDivider class="mb-6 mt-2" />

    <SwapEventFee
      v-model="hasFee"
      v-model:amount="states.feeAmount"
      v-model:asset="states.feeAsset"
      :location="states.location"
      :error-messages="{
        fee: toMessages(v$.feeAmount),
        amount: toMessages(v$.feeAsset),
      }"
    />

    <SwapEventNotes
      v-model="states.userNotes"
      :has-fee="hasFee"
      :error-messages="toMessages(v$.userNotes)"
      @blur="v$.userNotes.$touch()"
    />
  </div>
</template>

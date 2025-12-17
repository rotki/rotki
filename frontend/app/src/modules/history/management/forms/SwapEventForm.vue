<script setup lang="ts">
import type { GroupEventData } from '@/modules/history/management/forms/form-types';
import type { ValidationErrors } from '@/types/api/errors';
import type { AddSwapEventPayload, FeeEntry, SwapEvent, SwapEventUserNotes } from '@/types/history/events/schemas';
import { assert, HistoryEventEntryType } from '@rotki/common';
import useVuelidate from '@vuelidate/core';
import dayjs from 'dayjs';
import { omit } from 'es-toolkit';
import { isEmpty } from 'es-toolkit/compat';
import { useFormStateWatcher } from '@/composables/form';
import { useHistoryEvents } from '@/composables/history/events';
import { useEditModeStateTracker } from '@/composables/history/events/edit-mode-state';
import EventDateLocation from '@/modules/history/management/forms/common/EventDateLocation.vue';
import SimpleFeeList from '@/modules/history/management/forms/common/SimpleFeeList.vue';
import HistoryEventAssetPriceForm from '@/modules/history/management/forms/HistoryEventAssetPriceForm.vue';
import SwapEventNotes from '@/modules/history/management/forms/swap/SwapEventNotes.vue';
import { useEventFormValidation } from '@/modules/history/management/forms/use-event-form-validation';
import { useMessageStore } from '@/store/message';
import { useRefPropVModel } from '@/utils/model';
import { toMessages } from '@/utils/validation';

interface FormData {
  entryType: typeof HistoryEventEntryType.SWAP_EVENT;
  fees: FeeEntry[];
  location: string;
  receiveAmount: string;
  receiveAsset: string;
  spendAmount: string;
  spendAsset: string;
  timestamp: number;
  uniqueId: string;
  userNotes: SwapEventUserNotes;
}

const stateUpdated = defineModel<boolean>('stateUpdated', { default: false, required: false });

const props = defineProps<{ data: GroupEventData<SwapEvent> }>();

function emptyEvent(): FormData {
  return {
    entryType: HistoryEventEntryType.SWAP_EVENT,
    fees: [],
    location: '',
    receiveAmount: '0',
    receiveAsset: '',
    spendAmount: '0',
    spendAsset: '',
    timestamp: dayjs().valueOf(),
    uniqueId: '',
    userNotes: ['', ''],
  };
}

function createUserNotes(spendNote: string, receiveNote: string, ...feeNotes: string[]): SwapEventUserNotes {
  return [spendNote, receiveNote, ...feeNotes];
}

const states = ref<FormData>(emptyEvent());
const hasFee = ref<boolean>(false);
const identifiers = ref<number[]>();
const errorMessages = ref<Record<string, string[]>>({});
const spendAssetPriceForm = useTemplateRef<InstanceType<typeof HistoryEventAssetPriceForm>>('spendAssetPriceForm');
const receiveAssetPriceForm = useTemplateRef<InstanceType<typeof HistoryEventAssetPriceForm>>('receiveAssetPriceForm');

const timestamp = useRefPropVModel(states, 'timestamp');

const { t } = useI18n({ useScope: 'global' });

const { createCommonRules } = useEventFormValidation();
const commonRules = createCommonRules();

const rules = {
  fees: commonRules.createExternalValidationRule(),
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

async function submitAllPrices(): Promise<boolean> {
  const lists = [
    get(spendAssetPriceForm),
    get(receiveAssetPriceForm),
  ].filter(Boolean);

  for (const list of lists) {
    if (!list) {
      continue;
    }
    const result = await list.submitPrice();
    if (result && !result.success) {
      handleValidationErrors(result.message || t('transactions.events.form.asset_price.failed'));
      return false;
    }
  }

  return true;
}

async function save(): Promise<boolean> {
  if (!(await get(v$).$validate())) {
    return false;
  }

  const isEditMode = isDefined(identifiers);

  // Submit prices from all nested HistoryEventAssetPriceForm components
  const pricesSubmitted = await submitAllPrices();
  if (!pricesSubmitted) {
    return false;
  }

  if (shouldSkipSave(isEditMode, get(states))) {
    return true;
  }

  const model = get(states);
  const fees = get(hasFee) ? model.fees.filter(fee => fee.amount && fee.asset) : undefined;
  const feeCount = fees?.length ?? 0;
  // Only include userNotes for spend, receive, and actual fees (2 + fee count)
  const userNotes = createUserNotes(model.userNotes[0], model.userNotes[1], ...model.userNotes.slice(2, 2 + feeCount));
  const payload: AddSwapEventPayload = {
    ...omit(model, ['fees', 'userNotes']),
    fees,
    userNotes,
  };

  const eventIdentifiers = get(identifiers);
  const result = isEditMode
    ? await editHistoryEvent({
        ...omit(payload, ['uniqueId']),
        identifiers: eventIdentifiers!,
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
  const feeEvents = data.eventsInGroup.filter(item => item.eventSubtype === 'fee');

  assert(spend);
  assert(receive);

  const hasFeeEvents = feeEvents.length > 0;
  set(hasFee, hasFeeEvents);
  // Collect all identifiers: [spendId, receiveId, ...feeIds]
  const allIdentifiers = [
    spend.identifier,
    receive.identifier,
    ...feeEvents.map(fee => fee.identifier),
  ];
  set(identifiers, allIdentifiers);

  const fees: FeeEntry[] = feeEvents.map(fee => ({
    amount: fee.amount.toString(),
    asset: fee.asset,
  }));

  const userNotes: SwapEventUserNotes = hasFeeEvents
    ? [getNotes(spend), getNotes(receive), ...feeEvents.map(fee => getNotes(fee))]
    : [getNotes(spend), getNotes(receive)];

  set(states, {
    entryType: HistoryEventEntryType.SWAP_EVENT,
    fees,
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
  const oldStates = get(states);
  if (hasFee) {
    // When enabling fees, ensure there's at least one empty fee entry and fee note
    const updates: Partial<FormData> = {};
    if (oldStates.fees.length === 0) {
      updates.fees = [{ amount: '', asset: '' }];
    }
    // Add empty fee note if not present
    if (oldStates.userNotes.length < 3) {
      updates.userNotes = createUserNotes(oldStates.userNotes[0], oldStates.userNotes[1], ...oldStates.userNotes.slice(2), '');
    }
    if (Object.keys(updates).length > 0) {
      set(states, {
        ...oldStates,
        ...updates,
      });
    }
    return;
  }
  // When disabling fees, remove fee entries and keep only spend/receive notes
  set(states, {
    ...oldStates,
    fees: [],
    userNotes: createUserNotes(oldStates.userNotes[0], oldStates.userNotes[1]),
  });
});

// Sync userNotes array with fees array when fees are added/removed
watch(() => get(states).fees.length, (newLength, oldLength) => {
  if (!get(hasFee))
    return;

  const currentNotes = get(states).userNotes;
  const expectedLength = 2 + newLength; // 2 for spend/receive + fee count

  if (currentNotes.length === expectedLength)
    return;

  if (newLength > oldLength) {
    // Fee added - add empty notes
    const notesToAdd = newLength - oldLength;
    const newNotes = createUserNotes(currentNotes[0], currentNotes[1], ...currentNotes.slice(2), ...new Array<string>(notesToAdd).fill(''));
    set(states, { ...get(states), userNotes: newNotes });
  }
  else {
    // Fee removed - remove corresponding notes from the end
    const newNotes = createUserNotes(currentNotes[0], currentNotes[1], ...currentNotes.slice(2, expectedLength));
    set(states, { ...get(states), userNotes: newNotes });
  }
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
      v-model:timestamp="timestamp"
      v-model:location="states.location"
      :location-disabled="data.type !== 'add'"
      :error-messages="{
        location: toMessages(v$.location),
        timestamp: toMessages(v$.timestamp),
      }"
      @blur="v$[$event].$touch()"
    />

    <RuiDivider class="mb-6 mt-2" />

    <HistoryEventAssetPriceForm
      ref="spendAssetPriceForm"
      v-model:amount="states.spendAmount"
      v-model:asset="states.spendAsset"
      hide-price-fields
      :timestamp="timestamp"
      :v$="{
        ...v$,
        asset: v$.spendAsset,
        amount: v$.spendAmount,
      }"
      :location="states.location"
      type="spend"
    />

    <HistoryEventAssetPriceForm
      ref="receiveAssetPriceForm"
      v-model:amount="states.receiveAmount"
      v-model:asset="states.receiveAsset"
      hide-price-fields
      :timestamp="timestamp"
      :v$="{
        ...v$,
        asset: v$.receiveAsset,
        amount: v$.receiveAmount,
      }"
      :location="states.location"
      type="receive"
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

    <RuiCheckbox
      v-model="hasFee"
      :label="t('transactions.events.form.has_fee.label')"
      data-cy="has-fee"
      color="primary"
    />

    <SimpleFeeList
      v-model="states.fees"
      :disabled="!hasFee"
      :location="states.location"
    />

    <SwapEventNotes
      v-model="states.userNotes"
      :fee-count="hasFee ? states.fees.length : 0"
      :error-messages="toMessages(v$.userNotes)"
      @blur="v$.userNotes.$touch()"
    />
  </div>
</template>

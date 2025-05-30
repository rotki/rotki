<script lang="ts" setup>
import type { EvmSwapFormData } from '@/modules/history/management/forms/evm-swap-event-form';
import type { GroupEventData, StandaloneEventData } from '@/modules/history/management/forms/form-types';
import type { ValidationErrors } from '@/types/api/errors';
import type { AddEvmSwapEventPayload, EvmHistoryEvent, EvmSwapEvent, SwapSubEventModel } from '@/types/history/events';
import AmountInput from '@/components/inputs/AmountInput.vue';
import CounterpartyInput from '@/components/inputs/CounterpartyInput.vue';
import { useFormStateWatcher } from '@/composables/form';
import { useHistoryEvents } from '@/composables/history/events';
import EventDateLocation from '@/modules/history/management/forms/common/EventDateLocation.vue';
import SwapSubEventList from '@/modules/history/management/forms/swap/SwapSubEventList.vue';
import { useEventFormValidation } from '@/modules/history/management/forms/use-event-form-validation';
import { toSubEvent, useDateTime } from '@/modules/history/management/forms/utils';
import { useMessageStore } from '@/store/message';
import { toMessages } from '@/utils/validation';
import { assert, HistoryEventEntryType } from '@rotki/common';
import useVuelidate from '@vuelidate/core';
import dayjs from 'dayjs';
import { isEmpty } from 'es-toolkit/compat';

const stateUpdated = defineModel<boolean>('stateUpdated', { default: false, required: false });

const props = defineProps<{ data: StandaloneEventData<EvmHistoryEvent> | GroupEventData<EvmSwapEvent> }>();

function emptySubEvent(): SwapSubEventModel {
  return {
    amount: '',
    asset: '',
  };
}

function emptyEvent(): EvmSwapFormData {
  return {
    address: '',
    counterparty: '',
    entryType: HistoryEventEntryType.EVM_SWAP_EVENT,
    fee: [],
    location: '',
    receive: [emptySubEvent()],
    sequenceIndex: '0',
    spend: [emptySubEvent()],
    timestamp: dayjs().valueOf(),
    txHash: '',
  };
}

const states = ref<EvmSwapFormData>(emptyEvent());
const hasFee = ref<boolean>(false);
const identifiers = ref<number[]>([]);
const errorMessages = ref<Record<string, string[]>>({});

const datetime = useDateTime(states);

const { t } = useI18n({ useScope: 'global' });
const { createCommonRules } = useEventFormValidation();
const commonRules = createCommonRules();

const rules = computed(() => ({
  address: commonRules.createValidEthAddressRule(),
  counterparty: commonRules.createExternalValidationRule(),
  fee: get(hasFee) ? commonRules.createRequiredAtLeastOne() : {},
  location: commonRules.createRequiredLocationRule(),
  receive: commonRules.createRequiredAtLeastOne(),
  sequenceIndex: commonRules.createRequiredSequenceIndexRule(),
  spend: commonRules.createRequiredAtLeastOne(),
  timestamp: commonRules.createExternalValidationRule(),
  txHash: commonRules.createValidTxHashRule(),
}));

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

  const payload: AddEvmSwapEventPayload = { ...get(states) };

  if (!get(hasFee)) {
    delete payload.fee;
  }

  if (payload.address === '') {
    payload.address = undefined;
  }

  const result = get(identifiers).length > 0
    ? await editHistoryEvent({
      ...payload,
      ...{
        identifiers: get(identifiers),
      },
    })
    : await addHistoryEvent(payload);

  if (result.success) {
    set(states, emptyEvent());
    set(identifiers, []);
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

watchImmediate(() => props.data, (data) => {
  if (data.type === 'group-add') {
    const group = data.group;

    set(states, {
      ...get(states),
      location: group.location ?? '',
      sequenceIndex: data.nextSequenceId.toString(),
      timestamp: group.timestamp,
      txHash: group.txHash,
    });
  }
  else if (data.type === 'edit-group') {
    const spend = data.eventsInGroup.filter(item => item.eventSubtype === 'spend');
    const receive = data.eventsInGroup.filter(item => item.eventSubtype === 'receive');
    const fee = data.eventsInGroup.filter(item => item.eventSubtype === 'fee');

    assert(spend.length > 0);
    assert(receive.length > 0);

    set(hasFee, fee.length > 0);
    set(identifiers, data.eventsInGroup.map(item => item.identifier));

    const firstSpend = spend[0];
    set(states, {
      address: firstSpend.address ?? '',
      counterparty: firstSpend.counterparty ?? '',
      entryType: HistoryEventEntryType.EVM_SWAP_EVENT,
      fee: fee.map(event => toSubEvent(event)),
      location: firstSpend.location,
      receive: receive.map(event => toSubEvent(event)),
      sequenceIndex: firstSpend.sequenceIndex.toString(),
      spend: spend.map(event => toSubEvent(event)),
      timestamp: firstSpend.timestamp,
      txHash: firstSpend.txHash,
    });
  }
});

watch(hasFee, (hasFee) => {
  set(states, { ...get(states), fee: hasFee ? [emptySubEvent()] : [] });
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
      location-disabled
      :error-messages="{
        location: toMessages(v$.location),
        datetime: toMessages(v$.timestamp),
      }"
      @blur="v$[$event].$touch()"
    />

    <RuiDivider class="mb-6 mt-2" />

    <RuiTextField
      v-model="states.txHash"
      variant="outlined"
      color="primary"
      disabled
      data-cy="tx-hash"
      :label="t('common.tx_hash')"
      :error-messages="toMessages(v$.txHash)"
      @blur="v$.txHash.$touch()"
    />

    <RuiDivider class="mb-6 mt-2" />

    <SwapSubEventList
      v-model="states.spend"
      data-cy="spend"
      :location="states.location"
      type="spend"
    />

    <RuiDivider class="mb-6 mt-2" />

    <SwapSubEventList
      v-model="states.receive"
      data-cy="receive"
      :location="states.location"
      type="receive"
    />

    <RuiDivider class="mb-6 mt-2" />

    <RuiCheckbox
      v-model="hasFee"
      :label="t('transactions.events.form.has_fee.label')"
      data-cy="has-fee"
      color="primary"
    />

    <SwapSubEventList
      v-model="states.fee"
      data-cy="fee"
      :location="states.location"
      :disabled="!hasFee"
      type="fee"
    />

    <RuiDivider class="mb-6 mt-2" />

    <RuiTextField
      v-model="states.address"
      clearable
      variant="outlined"
      data-cy="address"
      :label="t('transactions.events.form.contract_address.label')"
      :error-messages="errorMessages.address"
      @blur="v$.address.$touch()"
    />

    <div class="grid md:grid-cols-2 gap-4">
      <AmountInput
        v-model="states.sequenceIndex"
        variant="outlined"
        integer
        :disabled="data.type === 'edit-group'"
        data-cy="sequence-index"
        :label="t('transactions.events.form.sequence_index.label')"
        :error-messages="toMessages(v$.sequenceIndex)"
        @blur="v$.sequenceIndex.$touch()"
      />

      <CounterpartyInput
        v-model="states.counterparty"
        :label="t('common.counterparty')"
        data-cy="counterparty"
        :error-messages="toMessages(v$.counterparty)"
        @blur="v$.counterparty.$touch()"
      />
    </div>
  </div>
</template>

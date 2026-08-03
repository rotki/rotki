<script lang="ts" setup>
import type { SolanaEvent, SolanaSwapEvent } from '@/modules/history/events/schemas';
import type { GroupEventData, StandaloneEventData } from '@/modules/history/management/forms/form-types';
import { SOLANA_CHAIN } from '@/modules/assets/types';
import CounterpartyInput from '@/modules/history/events/mapping/CounterpartyInput.vue';
import EventDateLocation from '@/modules/history/management/forms/common/EventDateLocation.vue';
import { collectPriceIntents } from '@/modules/history/management/forms/price-intent';
import {
  emptySolanaSwapForm,
  solanaSwapSchema,
  solanaSwapStateFromEvents,
  toSolanaSwapPayload,
} from '@/modules/history/management/forms/solana-swap-event-form';
import { emptySubEvent } from '@/modules/history/management/forms/swap/swap-sub-event';
import SwapSubEventList from '@/modules/history/management/forms/swap/SwapSubEventList.vue';
import { useHistoryEventForm } from '@/modules/history/management/forms/use-history-event-form';
import AmountInput from '@/modules/shell/components/inputs/AmountInput.vue';

const stateUpdated = defineModel<boolean>('stateUpdated', { default: false, required: false });

const { data } = defineProps<{ data: StandaloneEventData<SolanaEvent> | GroupEventData<SolanaSwapEvent> }>();

const { t } = useI18n({ useScope: 'global' });

// A Solana swap is always on Solana, so the location is displayed but never edited or sent.
const location = ref<string>(SOLANA_CHAIN);

const { form, save, seed } = useHistoryEventForm({
  initial: emptySolanaSwapForm,
  priceIntents: state => collectPriceIntents(state.spend, state.receive, state.fee),
  schema: solanaSwapSchema(),
  stateUpdated,
  toEditPayload: (payload, identifiers) => ({ ...payload, identifiers }),
  transform: toSolanaSwapPayload,
});

const { state } = form;

watchImmediate(() => data, (data) => {
  if (data.type === 'group-add') {
    const group = data.group;

    seed({
      ...emptySolanaSwapForm(),
      sequenceIndex: data.nextSequenceId.toString(),
      timestamp: group.timestamp,
      txRef: group.txRef,
    });
  }
  else if (data.type === 'edit-group') {
    seed(solanaSwapStateFromEvents(data.eventsInGroup), data.eventsInGroup.map(item => item.identifier));
  }
});

watch(() => state.hasFee, (hasFee) => {
  if (!hasFee) {
    state.fee = [];
    return;
  }

  // Seeding an existing group sets the flag and the rows together, so only an empty list wants a
  // blank row; replacing it unconditionally would discard what was just loaded.
  if (state.fee.length === 0)
    state.fee.push(emptySubEvent());
});

defineExpose({
  errorCount: form.errorCount,
  save,
});
</script>

<template>
  <div>
    <EventDateLocation
      v-model:timestamp="state.timestamp"
      v-model:location="location"
      location-disabled
      :error-messages="{
        location: form.errors('location'),
        timestamp: form.errors('timestamp'),
      }"
      @blur="form.touch($event)"
    />

    <RuiDivider class="mb-6 mt-2" />

    <RuiTextField
      v-model="state.txRef"
      variant="outlined"
      color="primary"
      :disabled="data.type !== 'add'"
      data-cy="tx-ref"
      :label="t('common.signature')"
      required
      :error-messages="form.errors('txRef')"
      @blur="form.touch('txRef')"
    />

    <RuiDivider class="mb-6 mt-2" />

    <SwapSubEventList
      v-model="state.spend"
      data-cy="spend"
      path="spend"
      :errors="form.errors"
      :touch="form.touch"
      :location="location"
      :timestamp="state.timestamp"
      type="spend"
    />

    <RuiDivider class="mb-6 mt-2" />

    <SwapSubEventList
      v-model="state.receive"
      data-cy="receive"
      path="receive"
      :errors="form.errors"
      :touch="form.touch"
      :location="location"
      :timestamp="state.timestamp"
      type="receive"
    />

    <RuiDivider class="mb-6 mt-2" />

    <RuiCheckbox
      v-model="state.hasFee"
      :label="t('transactions.events.form.has_fee.label')"
      data-cy="has-fee"
      color="primary"
    />

    <SwapSubEventList
      v-model="state.fee"
      data-cy="fee"
      path="fee"
      :errors="form.errors"
      :touch="form.touch"
      :location="location"
      :disabled="!state.hasFee"
      :timestamp="state.timestamp"
      type="fee"
    />

    <RuiDivider class="mb-6 mt-2" />

    <RuiTextField
      v-model="state.address"
      clearable
      variant="outlined"
      data-cy="address"
      :label="t('transactions.events.form.contract_address.label')"
      :error-messages="form.errors('address')"
      @blur="form.touch('address')"
    />

    <div class="grid md:grid-cols-2 gap-4">
      <AmountInput
        v-model="state.sequenceIndex"
        variant="outlined"
        integer
        :disabled="data.type === 'edit-group'"
        data-cy="sequence-index"
        :label="t('transactions.events.form.sequence_index.label')"
        required
        :error-messages="form.errors('sequenceIndex')"
        @blur="form.touch('sequenceIndex')"
      />

      <CounterpartyInput
        v-model="state.counterparty"
        :label="t('common.counterparty')"
        data-cy="counterparty"
        :error-messages="form.errors('counterparty')"
        @blur="form.touch('counterparty')"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import type { SwapEvent } from '@/modules/history/events/schemas';
import type { GroupEventData } from '@/modules/history/management/forms/form-types';
import type { PriceIntent } from '@/modules/history/management/forms/price-intent';
import { generateUUID } from '@shared/utils';
import EventDateLocation from '@/modules/history/management/forms/common/EventDateLocation.vue';
import SimpleFeeList from '@/modules/history/management/forms/common/SimpleFeeList.vue';
import HistoryEventAssetPriceForm from '@/modules/history/management/forms/HistoryEventAssetPriceForm.vue';
import {
  emptySwapFee,
  emptySwapForm,
  swapIdentifiers,
  swapSchema,
  swapStateFromEvents,
  toSwapEditPayload,
  toSwapPayload,
} from '@/modules/history/management/forms/swap-event-form';
import SwapEventNotes from '@/modules/history/management/forms/swap/SwapEventNotes.vue';
import { useFeeRows } from '@/modules/history/management/forms/swap/use-fee-rows';
import { useHistoryEventForm } from '@/modules/history/management/forms/use-history-event-form';

const stateUpdated = defineModel<boolean>('stateUpdated', { default: false, required: false });

const { data } = defineProps<{ data: GroupEventData<SwapEvent> }>();

const { t } = useI18n({ useScope: 'global' });

const { form, save, seed } = useHistoryEventForm({
  initial: emptySwapForm,
  priceIntentKeys: ['spendPriceIntent', 'receivePriceIntent'],
  priceIntents: (state) => {
    const intents: PriceIntent[] = [];
    if (state.spendPriceIntent)
      intents.push(state.spendPriceIntent);
    if (state.receivePriceIntent)
      intents.push(state.receivePriceIntent);
    return intents;
  },
  schema: swapSchema(),
  stateUpdated,
  toEditPayload: toSwapEditPayload,
  // A new swap needs an identifier of its own, which a pure transform cannot produce.
  transform: state => toSwapPayload(state, state.uniqueId || generateUUID()),
});

const { state } = form;

watchImmediate(() => data, (data) => {
  if (data.type !== 'edit-group')
    return;

  seed(swapStateFromEvents(data.eventsInGroup), swapIdentifiers(data.eventsInGroup));
});

useFeeRows(() => state.hasFee, () => state.fees, emptySwapFee);

defineExpose({
  errorCount: form.errorCount,
  save,
});
</script>

<template>
  <div>
    <EventDateLocation
      v-model:timestamp="state.timestamp"
      v-model:location="state.location"
      :location-disabled="data.type !== 'add'"
      :error-messages="{
        location: form.errors('location'),
        timestamp: form.errors('timestamp'),
      }"
      @blur="form.touch($event)"
    />

    <RuiDivider class="mb-6 mt-2" />

    <HistoryEventAssetPriceForm
      v-model:amount="state.spendAmount"
      v-model:asset="state.spendAsset"
      v-model:price-intent="state.spendPriceIntent"
      hide-price-fields
      :timestamp="state.timestamp"
      :error-messages="{
        amount: form.errors('spendAmount'),
        asset: form.errors('spendAsset'),
      }"
      :location="state.location"
      type="spend"
      @blur="form.touch($event === 'amount' ? 'spendAmount' : 'spendAsset')"
    />

    <HistoryEventAssetPriceForm
      v-model:amount="state.receiveAmount"
      v-model:asset="state.receiveAsset"
      v-model:price-intent="state.receivePriceIntent"
      hide-price-fields
      :timestamp="state.timestamp"
      :error-messages="{
        amount: form.errors('receiveAmount'),
        asset: form.errors('receiveAsset'),
      }"
      :location="state.location"
      type="receive"
      @blur="form.touch($event === 'amount' ? 'receiveAmount' : 'receiveAsset')"
    />

    <RuiTextField
      v-if="data.type !== 'edit-group'"
      v-model="state.uniqueId"
      variant="outlined"
      color="primary"
      data-testid="unique-id"
      :hint="t('swap_event_form.unique_id_hint')"
      :label="t('swap_event_form.unique_id')"
      :error-messages="form.errors('uniqueId')"
    />

    <RuiDivider class="mb-6 mt-2" />

    <RuiCheckbox
      v-model="state.hasFee"
      :label="t('transactions.events.form.has_fee.label')"
      data-testid="has-fee"
      color="primary"
    />

    <SimpleFeeList
      v-model="state.fees"
      path="fees"
      :errors="form.errors"
      :touch="form.touch"
      :disabled="!state.hasFee"
      :location="state.location"
    />

    <SwapEventNotes
      v-model:spend-notes="state.spendNotes"
      v-model:receive-notes="state.receiveNotes"
      v-model:fees="state.fees"
      :error-messages="form.errors('userNotes')"
      @blur="form.touch('userNotes')"
    />
  </div>
</template>

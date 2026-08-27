<script setup lang="ts">
import type { SolanaEvent } from '@/modules/history/events/schemas';
import type { StandaloneEventData } from '@/modules/history/management/forms/form-types';
import { HistoryEventEntryType } from '@rotki/common';
import { SOLANA_CHAIN } from '@/modules/assets/types';
import CounterpartyInput from '@/modules/history/events/mapping/CounterpartyInput.vue';
import { useHistoryEventCounterpartyMappings } from '@/modules/history/events/mapping/use-history-event-counterparty-mappings';
import EventDateLocation from '@/modules/history/management/forms/common/EventDateLocation.vue';
import { EVENT_PRICE_INTENT_KEYS } from '@/modules/history/management/forms/eth-block-event-form';
import HistoryEventAssetPriceForm from '@/modules/history/management/forms/HistoryEventAssetPriceForm.vue';
import HistoryEventTypeForm from '@/modules/history/management/forms/HistoryEventTypeForm.vue';
import {
  emptySolanaEventForm,
  solanaEventSchema,
  solanaEventStateFromEvent,
  solanaEventStateFromGroup,
  toSolanaEventEditPayload,
  toSolanaEventPayload,
} from '@/modules/history/management/forms/solana-event-form';
import { useHistoryEventForm } from '@/modules/history/management/forms/use-history-event-form';
import AmountInput from '@/modules/shell/components/inputs/AmountInput.vue';
import JsonInput from '@/modules/shell/components/inputs/JsonInput.vue';

interface HistoryEventFormProps {
  data: StandaloneEventData<SolanaEvent>;
}

const stateUpdated = defineModel<boolean>('stateUpdated', { default: false, required: false });

const { data } = defineProps<HistoryEventFormProps>();

const { t } = useI18n({ useScope: 'global' });

// A Solana event is always on Solana, so the location is displayed but never edited or sent.
const location = ref<string>(SOLANA_CHAIN);

const { counterparties } = useHistoryEventCounterpartyMappings();

const { form, save, seed } = useHistoryEventForm({
  initial: () => emptySolanaEventForm(data.nextSequenceId),
  priceIntentKeys: EVENT_PRICE_INTENT_KEYS,
  priceIntents: state => (state.priceIntent ? [state.priceIntent] : []),
  schema: computed(() => solanaEventSchema(data.type === 'edit', () => get(counterparties))),
  stateUpdated,
  toEditPayload: toSolanaEventEditPayload,
  transform: toSolanaEventPayload,
});

const { state } = form;

const isInformationalEvent = computed<boolean>(() => state.eventType === 'informational');

function touchEventType(): void {
  form.touch('eventType');
  form.touch('eventSubtype');
}

watchImmediate(() => data, (data) => {
  if (data.type === 'edit') {
    seed(solanaEventStateFromEvent(data.event, data.nextSequenceId), [data.event.identifier]);
    return;
  }

  seed(data.type === 'group-add'
    ? solanaEventStateFromGroup(data.group, data.nextSequenceId)
    : emptySolanaEventForm(data.nextSequenceId));
});

defineExpose({
  errorCount: form.errorCount,
  save,
});
</script>

<template>
  <div>
    <HistoryEventTypeForm
      v-model:event-type="state.eventType"
      v-model:event-subtype="state.eventSubtype"
      :counterparty="state.counterparty"
      :entry-type="HistoryEventEntryType.SOLANA_EVENT"
      :error-messages="{
        eventType: form.errors('eventType'),
        eventSubtype: form.errors('eventSubtype'),
      }"
      show-accounting-rule-link
      :dirty="stateUpdated"
      class="mb-4"
      @touch="touchEventType()"
    />

    <div class="grid md:grid-cols-2 gap-4 mb-4">
      <EventDateLocation
        v-model:timestamp="state.timestamp"
        v-model:location="location"
        class="col-span-2"
        location-disabled
        :error-messages="{
          location: form.errors('location'),
          timestamp: form.errors('timestamp'),
        }"
        @blur="form.touch($event)"
      />
    </div>

    <RuiTextField
      v-model="state.txRef"
      variant="outlined"
      color="primary"
      :disabled="data.type !== 'add'"
      data-testid="tx-ref"
      :label="t('common.signature')"
      required
      :error-messages="form.errors('txRef')"
      @blur="form.touch('txRef')"
    />

    <RuiDivider class="mb-6 mt-2" />

    <HistoryEventAssetPriceForm
      v-model:asset="state.asset"
      v-model:amount="state.amount"
      v-model:price-intent="state.priceIntent"
      :location="location"
      :error-messages="{
        amount: form.errors('amount'),
        asset: form.errors('asset'),
      }"
      :timestamp="state.timestamp"
      :no-price-fields="isInformationalEvent"
      @blur="form.touch($event)"
    />

    <RuiDivider class="mb-6 mt-2" />

    <div class="grid md:grid-cols-2 gap-4">
      <AmountInput
        v-model="state.sequenceIndex"
        variant="outlined"
        integer
        data-testid="sequence-index"
        :label="t('transactions.events.form.sequence_index.label')"
        required
        :error-messages="form.errors('sequenceIndex')"
        @blur="form.touch('sequenceIndex')"
      />
      <CounterpartyInput
        v-model="state.counterparty"
        :label="t('common.counterparty')"
        data-testid="counterparty"
        :error-messages="form.errors('counterparty')"
        @blur="form.touch('counterparty')"
      />
    </div>

    <RuiDivider class="mb-6 mt-2" />

    <RuiTextArea
      v-model="state.notes"
      prepend-icon="lu-sticky-note"
      data-testid="notes"
      variant="outlined"
      color="primary"
      max-rows="5"
      min-rows="3"
      auto-grow
      :label="t('common.notes')"
      :hint="t('transactions.events.form.notes.hint')"
      :error-messages="form.errors('notes')"
      @blur="form.touch('notes')"
    />

    <RuiDivider class="mb-2 mt-6" />

    <RuiAccordions>
      <RuiAccordion
        data-testid="solana-event-form-advance"
        :class-names="{ header: 'py-4' }"
        eager
      >
        <template #header>
          {{ t('transactions.events.form.advanced') }}
        </template>
        <div class="py-2">
          <RuiTextField
            v-model="state.groupIdentifier"
            variant="outlined"
            color="primary"
            data-testid="group-identifier"
            :disabled="state.hasActualGroupIdentifier"
            :label="t('transactions.events.form.group_identifier.label')"
            :error-messages="form.errors('groupIdentifier')"
            @blur="form.touch('groupIdentifier')"
          />

          <JsonInput
            v-model="state.extraData"
            :label="t('transactions.events.form.extra_data.label')"
          />
        </div>
      </RuiAccordion>
    </RuiAccordions>
  </div>
</template>

<script lang="ts" setup>
import LocationSelector from '@/modules/balances/LocationSelector.vue';
import CounterpartyInput from '@/modules/history/events/mapping/CounterpartyInput.vue';
import EventDetailsSection from '@/modules/history/management/forms/common/EventDetailsSection.vue';
import TxRefField from '@/modules/history/management/forms/common/TxRefField.vue';
import SwapSubEventList from '@/modules/history/management/forms/swap/SwapSubEventList.vue';
import { type SwapFormData, useSwapEventForm } from '@/modules/history/management/forms/use-swap-event-form';
import AmountInput from '@/modules/shell/components/inputs/AmountInput.vue';
import DateTimePicker from '@/modules/shell/components/inputs/DateTimePicker.vue';

const stateUpdated = defineModel<boolean>('stateUpdated', { default: false, required: false });

/** One form for the three swap entry types; a new swap takes its kind from its location. */
const { data } = defineProps<{
  data: SwapFormData;
}>();

const { t } = useI18n({ useScope: 'global' });

const {
  form,
  incomplete,
  isEvm,
  isPlain,
  lookupCanRetry,
  lookupHint,
  lookupLoading,
  retryLookup,
  save,
} = useSwapEventForm({ data: () => data, stateUpdated });

const { state } = form;

defineExpose({
  errorCount: form.errorCount,
  save,
});
</script>

<template>
  <div>
    <RuiAlert
      v-if="incomplete"
      type="error"
      data-testid="swap-event-form-incomplete"
    >
      {{ t('swap_event_form.incomplete') }}
    </RuiAlert>
    <template v-else>
      <LocationSelector
        v-model="state.location"
        :disabled="data.type !== 'add'"
        data-testid="location"
        :label="t('common.location')"
        required
        :error-messages="form.errors('location')"
        @blur="form.touch('location')"
      />

      <TxRefField
        v-if="!isPlain"
        v-model="state.txRef"
        :disabled="data.type !== 'add'"
        :label="isEvm ? t('common.tx_hash') : t('common.signature')"
        :hint="isEvm ? lookupHint : ''"
        :loading="lookupLoading"
        :can-retry="lookupCanRetry"
        :error-messages="form.errors('txRef')"
        @blur="form.touch('txRef')"
        @retry="retryLookup()"
      />
      <RuiTextField
        v-else-if="data.type !== 'edit-group'"
        v-model="state.uniqueId"
        color="primary"
        data-testid="unique-id"
        :hint="t('swap_event_form.unique_id_hint')"
        :label="t('swap_event_form.unique_id')"
        :error-messages="form.errors('uniqueId')"
      />

      <DateTimePicker
        v-model="state.timestamp"
        :label="t('common.datetime')"
        required
        max-date="now"
        accuracy="millisecond"
        data-testid="datetime"
        :hint="t('transactions.events.form.datetime.hint')"
        :error-messages="form.errors('timestamp')"
        @blur="form.touch('timestamp')"
      />

      <RuiDivider class="mb-6 mt-2" />

      <SwapSubEventList
        v-model="state.spend"
        data-testid="spend"
        path="spend"
        :errors="form.errors"
        :touch="form.touch"
        :location="state.location"
        :timestamp="state.timestamp"
        :plain="isPlain"
        type="spend"
      />

      <RuiDivider class="mb-6 mt-2" />

      <SwapSubEventList
        v-model="state.receive"
        data-testid="receive"
        path="receive"
        :errors="form.errors"
        :touch="form.touch"
        :location="state.location"
        :timestamp="state.timestamp"
        :plain="isPlain"
        type="receive"
      />

      <RuiDivider class="mb-6 mt-2" />

      <RuiCheckbox
        v-model="state.hasFee"
        :label="t('transactions.events.form.has_fee.label')"
        data-testid="has-fee"
        color="primary"
      />

      <SwapSubEventList
        v-if="state.hasFee"
        v-model="state.fee"
        data-testid="fee"
        path="fee"
        :errors="form.errors"
        :touch="form.touch"
        :location="state.location"
        :timestamp="state.timestamp"
        :plain="isPlain"
        type="fee"
      />

      <template v-if="!isPlain">
        <RuiDivider class="mb-6 mt-2" />

        <CounterpartyInput
          :model-value="state.counterparty"
          :label="t('common.counterparty')"
          data-testid="counterparty"
          :error-messages="form.errors('counterparty')"
          @blur="form.touch('counterparty')"
          @update:model-value="state.counterparty = $event ?? ''"
        />

        <RuiTextField
          v-model="state.address"
          clearable
          data-testid="address"
          :label="t('transactions.events.form.contract_address.label')"
          :error-messages="form.errors('address')"
          @blur="form.touch('address')"
        />

        <EventDetailsSection
          data-testid="swap-event-form-advance"
          :errors="form.errors"
          :paths="['sequenceIndex']"
        >
          <AmountInput
            v-model="state.sequenceIndex"
            integer
            :disabled="data.type === 'edit-group'"
            data-testid="sequence-index"
            :label="t('transactions.events.form.sequence_index.label')"
            required
            :error-messages="form.errors('sequenceIndex')"
            @blur="form.touch('sequenceIndex')"
          />
        </EventDetailsSection>
      </template>
    </template>
  </div>
</template>

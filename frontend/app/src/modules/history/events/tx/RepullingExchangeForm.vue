<script lang="ts" setup>
import type { ZodType } from 'zod';
import type { Exchange } from '@/modules/balances/types/exchanges';
import type { ValidationErrors } from '@/modules/core/api/types/errors';
import type { RepullingTransactionPayload } from '@/modules/history/events/event-payloads';
import { useExchangeData } from '@/modules/balances/exchanges/use-exchange-data';
import { toServerErrors } from '@/modules/core/form/server-errors';
import { type FormApi, useForm } from '@/modules/core/form/use-form';
import { type RepullingExchangeFormState, repullingExchangeSchema } from '@/modules/history/events/tx/repulling-forms';
import { shouldShowDateRangePicker } from '@/modules/history/events/tx/use-repulling-transaction-form';
import LocationIcon from '@/modules/shell/components/display/LocationIcon.vue';
import DateTimeRangePicker from '@/modules/shell/components/inputs/DateTimeRangePicker.vue';

const modelValue = defineModel<RepullingTransactionPayload>({ required: true });
const errors = defineModel<ValidationErrors>('errorMessages', { required: true });
const stateUpdated = defineModel<boolean>('stateUpdated', { default: false, required: false });

const { t } = useI18n({ useScope: 'global' });

const { syncingExchanges } = useExchangeData();

const hasNoExchanges = computed<boolean>(() => get(syncingExchanges).length === 0);

/*
 * `useForm` rather than `useModelForm`: the chosen exchange is the form's main field and is not part
 * of the shared payload, so the state is wider than the model. Only the range is mirrored back.
 */
const form: FormApi<RepullingExchangeFormState, RepullingExchangeFormState> = useForm({
  initial: (): RepullingExchangeFormState => ({
    // Spelled out, not left off: a key the state does not carry fails the schema on its absence
    // rather than on the rule, and reports zod's own message instead of the one below.
    exchange: undefined,
    fromTimestamp: get(modelValue).fromTimestamp,
    toTimestamp: get(modelValue).toTimestamp,
  }),
  // A getter, not a computed over `showDateRangePicker`: that reads the state this form owns, so
  // the two would be defined in terms of each other.
  schema: (): ZodType => repullingExchangeSchema({
    exchangeRequired: t('transactions.repulling.validation.exchange_non_empty'),
    rangeRequired: t('transactions.repulling.validation.date_non_empty'),
  }, shouldShowDateRangePicker(false, form.state.exchange)),
  // The dialog owns the persist and reads the range off the model.
  submit: async (): Promise<{ success: boolean }> => Promise.resolve({ success: true }),
  transform: (state): RepullingExchangeFormState => ({ ...state }),
});

const showDateRangePicker = computed<boolean>(() => shouldShowDateRangePicker(false, form.state.exchange));

watch(() => [form.state.fromTimestamp, form.state.toTimestamp], ([fromTimestamp, toTimestamp]) => {
  set(modelValue, { ...get(modelValue), fromTimestamp, toTimestamp });
});

watchImmediate(errors, (value) => {
  form.setServerErrors(toServerErrors(value));
}, { deep: true });

watch(form.dirty, (dirty) => {
  set(stateUpdated, dirty);
});

// An exchange that reports no range has no picker, so anything already in it is dropped rather than
// sent.
watch(showDateRangePicker, (show) => {
  if (!show) {
    form.state.fromTimestamp = undefined;
    form.state.toTimestamp = undefined;
  }
});

onBeforeUnmount(() => {
  set(errors, {});
});

onUnmounted(() => {
  set(stateUpdated, false);
});

defineExpose({
  getExchangeData: (): Exchange | undefined => form.state.exchange,
  validate: (): boolean => form.validate(),
});
</script>

<template>
  <div class="flex flex-col gap-4">
    <RuiAlert
      v-if="hasNoExchanges"
      type="warning"
    >
      <i18n-t
        keypath="transactions.repulling.no_exchanges"
        tag="span"
      >
        <template #link>
          <RouterLink :to="{ name: '/api-keys/exchanges/' }">
            <RuiButton
              color="primary"
              variant="text"
              size="sm"
              class="inline -my-1 [&>span]:underline"
            >
              {{ t('transactions.repulling.add_exchange_link') }}
            </RuiButton>
          </RouterLink>
        </template>
      </i18n-t>
    </RuiAlert>

    <template v-else>
      <RuiAutoComplete
        v-model="form.state.exchange"
        :options="syncingExchanges"
        :label="t('common.exchange')"
        variant="outlined"
        auto-select-first
        :item-height="48"
        text-attr="name"
        :error-messages="form.errors('exchange')"
        @update:model-value="form.touch('exchange')"
      >
        <template #selection="{ item }">
          <div class="flex items-center gap-2 pl-1">
            <LocationIcon
              icon
              size="20px"
              :item="item.location"
            />
            {{ item.name }}
          </div>
        </template>
        <template #item="{ item }">
          <div class="flex items-center gap-2">
            <LocationIcon
              icon
              :item="item.location"
            />
            {{ item.name }}
          </div>
        </template>
      </RuiAutoComplete>

      <DateTimeRangePicker
        v-if="showDateRangePicker"
        v-model:start="form.state.fromTimestamp"
        v-model:end="form.state.toTimestamp"
        allow-empty
        max-end-date="now"
        :start-error-messages="form.errors('fromTimestamp')"
        :end-error-messages="form.errors('toTimestamp')"
        @update:start="form.touch('fromTimestamp')"
        @update:end="form.touch('toTimestamp')"
      />
    </template>
  </div>
</template>

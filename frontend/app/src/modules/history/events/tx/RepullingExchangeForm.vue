<script lang="ts" setup>
import type { ZodType } from 'zod';
import type { Exchange } from '@/modules/balances/types/exchanges';
import type { ValidationErrors } from '@/modules/core/api/types/errors';
import type { RepullingTransactionPayload } from '@/modules/history/events/event-payloads';
import { useExchangeData } from '@/modules/balances/exchanges/use-exchange-data';
import { toServerErrors } from '@/modules/core/form/server-errors';
import { type FormApi, noSubmit, useForm } from '@/modules/core/form/use-form';
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

/**
 * Owns the exchange choice and the optional range this tab edits.
 *
 * @remarks
 * `useForm` rather than `useModelForm`: the chosen exchange is the form's main field and is not part
 * of the shared payload, so the state is wider than the model. Only the range is mirrored back.
 *
 * `schema` is a getter rather than a computed over `showDateRangePicker`: that computed reads the
 * state this form owns, so as a dependency the two would be defined in terms of each other.
 */
const form: FormApi<RepullingExchangeFormState, RepullingExchangeFormState> = useForm({
  initial: (): RepullingExchangeFormState => ({
    exchange: undefined,
    fromTimestamp: get(modelValue).fromTimestamp,
    toTimestamp: get(modelValue).toTimestamp,
  }),
  schema: (): ZodType => repullingExchangeSchema({
    exchangeRequired: t('transactions.repulling.validation.exchange_non_empty'),
    rangeRequired: t('transactions.repulling.validation.date_non_empty'),
  }, shouldShowDateRangePicker(false, form.state.exchange)),
  submit: noSubmit,
  transform: (state): RepullingExchangeFormState => ({ ...state }),
});

const showDateRangePicker = computed<boolean>(() => shouldShowDateRangePicker(false, form.state.exchange));

watch(() => [form.state.fromTimestamp, form.state.toTimestamp], ([fromTimestamp, toTimestamp]) => {
  set(modelValue, { ...get(modelValue), fromTimestamp, toTimestamp });
});

watchImmediate(errors, (value) => {
  form.setServerErrors(toServerErrors(value));
}, { deep: true });

/*
 * Immediate, like `useModelForm` does it. The flag belongs to the dialog and is shared with the two
 * sibling tabs, so a form arriving after an edited one has to hand it back disarmed; a plain watch
 * only ever raises it, and this form's own state never changes to trigger one.
 */
syncRefs(form.dirty, stateUpdated);

watch(showDateRangePicker, (show) => {
  if (!show) {
    form.state.fromTimestamp = undefined;
    form.state.toTimestamp = undefined;
  }
});

onBeforeUnmount(() => {
  set(errors, {});
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

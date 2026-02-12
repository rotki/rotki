<script lang="ts" setup>
import type { ValidationErrors } from '@/types/api/errors';
import type { Exchange } from '@/types/exchanges';
import type { RepullingTransactionPayload } from '@/types/history/events';
import useVuelidate from '@vuelidate/core';
import { required } from '@vuelidate/validators';
import LocationIcon from '@/components/history/LocationIcon.vue';
import DateTimeRangePicker from '@/components/inputs/DateTimeRangePicker.vue';
import { useFormStateWatcher } from '@/composables/form';
import { shouldShowDateRangePicker } from '@/composables/history/events/tx/use-repulling-transaction-form';
import { Routes } from '@/router/routes';
import { useGeneralSettingsStore } from '@/store/settings/general';
import { useSessionSettingsStore } from '@/store/settings/session';
import { useRefPropVModel } from '@/utils/model';
import { toMessages } from '@/utils/validation';

const modelValue = defineModel<RepullingTransactionPayload>({ required: true });
const errors = defineModel<ValidationErrors>('errorMessages', { required: true });
const stateUpdated = defineModel<boolean>('stateUpdated', { default: false, required: false });

const { t } = useI18n({ useScope: 'global' });

const chain = useRefPropVModel(modelValue, 'chain');
const fromTimestamp = useRefPropVModel(modelValue, 'fromTimestamp');
const toTimestamp = useRefPropVModel(modelValue, 'toTimestamp');

const exchange = ref<Exchange>();

const { connectedExchanges } = storeToRefs(useSessionSettingsStore());
const { nonSyncingExchanges } = storeToRefs(useGeneralSettingsStore());

const availableExchanges = computed<Exchange[]>(() => get(connectedExchanges).filter(
  exchange => !get(nonSyncingExchanges).some(
    excluded => excluded.location === exchange.location && excluded.name === exchange.name,
  ),
));

const hasNoExchanges = computed<boolean>(() => get(availableExchanges).length === 0);

const showDateRangePicker = computed<boolean>(() => shouldShowDateRangePicker(false, get(exchange)));

const rules = computed(() => {
  const timestampRules = get(showDateRangePicker) ? { required } : {};
  return {
    chain: { required },
    exchange: { required },
    fromTimestamp: timestampRules,
    toTimestamp: timestampRules,
  };
});

const states = {
  chain,
  exchange,
  fromTimestamp,
  toTimestamp,
};

const v$ = useVuelidate(
  rules,
  states,
  {
    $autoDirty: true,
    $externalResults: errors,
  },
);

useFormStateWatcher(states, stateUpdated);

onBeforeUnmount(() => {
  set(errors, {});
});

watch(showDateRangePicker, (show) => {
  if (!show) {
    set(modelValue, {
      ...get(modelValue),
      fromTimestamp: undefined,
      toTimestamp: undefined,
    });
  }
});

defineExpose({
  getExchangeData: () => get(exchange),
  validate: () => get(v$).$validate(),
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
          <RouterLink :to="Routes.API_KEYS_EXCHANGES">
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
        v-model="exchange"
        :options="availableExchanges"
        :label="t('common.exchange')"
        variant="outlined"
        auto-select-first
        :item-height="48"
        text-attr="name"
        :error-messages="toMessages(v$.exchange)"
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
        v-model:start="fromTimestamp"
        v-model:end="toTimestamp"
        allow-empty
        max-end-date="now"
        :start-error-messages="toMessages(v$.fromTimestamp)"
        :end-error-messages="toMessages(v$.toTimestamp)"
      />
    </template>
  </div>
</template>

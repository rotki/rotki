<script setup lang="ts">
import { startPromise } from '@shared/utils';
import { useExchangeApi } from '@/modules/balances/api/use-exchange-api';
import DateTimePicker from '@/modules/shell/components/inputs/DateTimePicker.vue';

const modelValue = defineModel<number>({ required: true });

const { errorMessages = [] } = defineProps<{
  errorMessages?: string[];
}>();

const loading = ref<boolean>(false);

const { queryBinanceHistoryStartTimestamp } = useExchangeApi();
const { t } = useI18n({ useScope: 'global' });

async function populateHistoryStartTimestamp(): Promise<void> {
  set(loading, true);
  set(modelValue, Math.floor(Date.now() / 1000));
  try {
    set(modelValue, await queryBinanceHistoryStartTimestamp());
  }
  finally {
    set(loading, false);
  }
}

onMounted(() => {
  startPromise(populateHistoryStartTimestamp());
});
</script>

<template>
  <DateTimePicker
    v-model="modelValue"
    class="mt-4"
    data-testid="binance-history-start"
    :disabled="loading"
    :error-messages="errorMessages"
    :hint="t('exchange_keys_form.binance_history_import.start_date_hint')"
    :label="t('exchange_keys_form.binance_history_import.start_date')"
    max-date="now"
    type="epoch"
    variant="outlined"
  />
</template>

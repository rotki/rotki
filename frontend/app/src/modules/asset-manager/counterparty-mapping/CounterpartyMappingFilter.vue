<script lang="ts" setup>
import CounterpartyInput from '@/components/inputs/CounterpartyInput.vue';

const counterparty = defineModel<string | undefined>('counterparty', { required: true });

const symbol = defineModel<string>('symbol', { required: true });

const symbolDebounced = computed<string>({
  get: () => get(symbol),
  set: useDebounceFn((value: string) => {
    set(symbol, value);
  }, 500),
});

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <div class="w-full md:w-[40rem] flex flex-col sm:flex-row gap-4">
    <CounterpartyInput
      v-model="counterparty"
      :label="t('asset_management.counterparty_mapping.filter_by_counterparty')"
      class="w-full"
      dense
      hide-details
      clearable
    />
    <RuiTextField
      v-model="symbolDebounced"
      class="w-full sm:max-w-72"
      variant="outlined"
      color="primary"
      :label="t('asset_management.cex_mapping.filter_by_location_symbol')"
      clearable
      hide-details
      dense
    />
  </div>
</template>

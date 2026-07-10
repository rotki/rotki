<script setup lang="ts">
import { type SupportedCurrency, useCurrencies } from '@/modules/assets/amount-display/currencies';
import { useClearableMessages } from '@/modules/settings/use-clearable-messages';
import { useSettingModel } from '@/modules/settings/use-setting-model';
import ListItem from '@/modules/shell/components/ListItem.vue';

const { currencies } = useCurrencies();

const { t } = useI18n({ useScope: 'global' });

const { error: writeError, model, success: writeSuccess } = useSettingModel('currency');
const { clearAll, error, setError, setSuccess, success } = useClearableMessages();

// The registry stores a Currency object; the select binds its ticker symbol and maps back on change.
const selectedCurrency = computed<SupportedCurrency>({
  get: () => get(model).tickerSymbol,
  set: (ticker) => {
    const currency = get(currencies).find(item => item.tickerSymbol === ticker);
    if (currency)
      set(model, currency);
  },
});

watch(model, () => {
  clearAll();
});

watch(writeSuccess, (saved) => {
  if (saved)
    setSuccess(t('general_settings.validation.currency.success', { symbol: get(selectedCurrency) }), true);
});

watch(writeError, (message) => {
  if (message)
    setError(`${t('general_settings.validation.currency.error')}: ${message}`, true);
});

function calculateFontSize(symbol: string): string {
  const length = symbol.length;
  return `${2.4 - length * 0.4}em`;
}
</script>

<template>
  <RuiMenuSelect
    v-model="selectedCurrency"
    class="mb-4"
    data-cy="currency-selector"
    :label="t('general_settings.amount.labels.main_currency')"
    :options="currencies"
    text-attr="tickerSymbol"
    key-attr="tickerSymbol"
    :item-height="68"
    variant="outlined"
    :success-messages="success"
    :error-messages="error"
  >
    <template #item="{ item }">
      <ListItem
        :id="`currency__${item.tickerSymbol.toLocaleLowerCase()}`"
        no-hover
        no-padding
        class="!py-0"
        :title="item.name"
        :subtitle="t('general_settings.amount.labels.main_currency_subtitle')"
      >
        <template #avatar>
          <div
            class="font-bold text-rui-primary"
            :style="{ fontSize: calculateFontSize(item.unicodeSymbol) }"
          >
            {{ item.unicodeSymbol }}
          </div>
        </template>
      </ListItem>
    </template>
  </RuiMenuSelect>
</template>

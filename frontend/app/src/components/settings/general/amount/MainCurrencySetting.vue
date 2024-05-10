<script setup lang="ts">
import { type Currency, useCurrencies } from '@/types/currencies';

const { currencies } = useCurrencies();
const selectedCurrency = ref<Currency>(get(currencies)[0]);
const { currency } = storeToRefs(useGeneralSettingsStore());
const { t } = useI18n();

const currenciesWithKeys = computed(() => get(currencies).map(c => ({ ...c, key: c.tickerSymbol })));

function successMessage(symbol: string) {
  return t('general_settings.validation.currency.success', {
    symbol,
  });
}

onMounted(() => {
  set(selectedCurrency, get(currency));
});

function calculateFontSize(symbol: string) {
  const length = symbol.length;
  return `${2.4 - length * 0.4}em`;
}
</script>

<template>
  <SettingsOption
    #default="{ error, success, updateImmediate }"
    setting="mainCurrency"
    :error-message="t('general_settings.validation.currency.error')"
    :success-message="successMessage"
  >
    <RuiMenuSelect
      v-model="selectedCurrency"
      class="general-settings__fields__currency-selector"
      :label="t('general_settings.amount.labels.main_currency')"
      :options="currenciesWithKeys"
      text-attr="tickerSymbol"
      :item-height="68"
      full-width
      show-details
      variant="outlined"
      :success-messages="success"
      :error-messages="error"
      @input="updateImmediate($event?.tickerSymbol)"
    >
      <template #item.text="{ option }">
        <ListItem
          :id="`currency__${option.tickerSymbol.toLocaleLowerCase()}`"
          no-hover
          no-padding
          class="!py-0"
          :title="option.name"
          :subtitle="t('general_settings.amount.labels.main_currency_subtitle')"
        >
          <template #avatar>
            <div
              class="font-bold text-rui-primary"
              :style="{ fontSize: calculateFontSize(option.unicodeSymbol) }"
            >
              {{ option.unicodeSymbol }}
            </div>
          </template>
        </ListItem>
      </template>
    </RuiMenuSelect>
  </SettingsOption>
</template>

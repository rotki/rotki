<script setup lang="ts">
import { type SupportedCurrency, useCurrencies } from '@/modules/assets/amount-display/currencies';
import { useCurrencyUpdate } from '@/modules/assets/prices/use-currency-update';
import SettingsOption from '@/modules/settings/controls/SettingsOption.vue';
import { useGeneralSettingsStore } from '@/modules/settings/use-general-settings-store';
import ListItem from '@/modules/shell/components/ListItem.vue';

const { currencies } = useCurrencies();
const selectedCurrency = ref<SupportedCurrency>(get(currencies)[0].tickerSymbol);

const { currency } = storeToRefs(useGeneralSettingsStore());
const { t } = useI18n({ useScope: 'global' });
const { onCurrencyUpdate } = useCurrencyUpdate();

function successMessage(symbol: string) {
  return t('general_settings.validation.currency.success', {
    symbol,
  });
}

onMounted(() => {
  set(selectedCurrency, get(currency).tickerSymbol);
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
    @finish="onCurrencyUpdate()"
  >
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
      @update:model-value="updateImmediate($event)"
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
  </SettingsOption>
</template>

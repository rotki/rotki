<script setup lang="ts">
import ListItem from '@/components/common/ListItem.vue';
import SettingsOption from '@/components/settings/controls/SettingsOption.vue';
import { useCurrencyUpdate } from '@/composables/use-currency-update';
import { useGeneralSettingsStore } from '@/store/settings/general';
import { type SupportedCurrency, useCurrencies } from '@/types/currencies';

const { currencies } = useCurrencies();
const selectedCurrency = ref<SupportedCurrency>(get(currencies)[0].tickerSymbol);

const { currency } = storeToRefs(useGeneralSettingsStore());
const { t } = useI18n();
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

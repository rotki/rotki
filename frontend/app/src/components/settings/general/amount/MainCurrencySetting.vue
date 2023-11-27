<script setup lang="ts">
import { type Currency, useCurrencies } from '@/types/currencies';

const { currencies } = useCurrencies();
const selectedCurrency = ref<Currency>(get(currencies)[0]);
const { currency } = storeToRefs(useGeneralSettingsStore());
const { t } = useI18n();

const successMessage = (symbol: string) =>
  t('general_settings.validation.currency.success', {
    symbol
  });

onMounted(() => {
  set(selectedCurrency, get(currency));
});

const calculateFontSize = (symbol: string) => {
  const length = symbol.length;
  return `${2.4 - length * 0.4}em`;
};
</script>

<template>
  <SettingsOption
    #default="{ error, success, update }"
    setting="mainCurrency"
    :error-message="t('general_settings.validation.currency.error')"
    :success-message="successMessage"
  >
    <VSelect
      v-model="selectedCurrency"
      outlined
      class="general-settings__fields__currency-selector"
      :label="t('general_settings.amount.labels.main_currency')"
      item-text="tickerSymbol"
      return-object
      :items="currencies"
      :success-messages="success"
      :error-messages="error"
      @change="update($event ? $event.tickerSymbol : $event)"
    >
      <template #item="{ item, attrs, on }">
        <VListItem
          :id="`currency__${item.tickerSymbol.toLocaleLowerCase()}`"
          v-bind="attrs"
          v-on="on"
        >
          <VListItemAvatar
            class="general-settings__currency-list primary--text font-bold"
            :style="{ fontSize: calculateFontSize(item.unicodeSymbol) }"
          >
            {{ item.unicodeSymbol }}
          </VListItemAvatar>
          <VListItemContent>
            <VListItemTitle>
              {{ item.name }}
            </VListItemTitle>
            <VListItemSubtitle>
              {{ t('general_settings.amount.labels.main_currency_subtitle') }}
            </VListItemSubtitle>
          </VListItemContent>
        </VListItem>
      </template>
    </VSelect>
  </SettingsOption>
</template>

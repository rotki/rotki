<script setup lang="ts">
import { type Currency, useCurrencies } from '@/types/currencies';

const { update } = useSettingsStore();
const { currency } = storeToRefs(useGeneralSettingsStore());

const filter = ref<string>('');
const visible = ref<boolean>(false);

const { t } = useI18n();
const { currencies } = useCurrencies();

const filteredCurrencies = computed<Currency[]>(() => {
  const filterValue = get(filter).toLocaleLowerCase();
  const supportedCurrencies = get(currencies);
  if (!filterValue) {
    return supportedCurrencies;
  }
  return supportedCurrencies.filter(({ name, tickerSymbol }) => {
    const currencyName = name.toLocaleLowerCase();
    const symbol = tickerSymbol.toLocaleLowerCase();
    return currencyName.includes(filterValue) || symbol.includes(filterValue);
  });
});

const onSelected = async (newCurrency: Currency) => {
  set(visible, false);
  if (newCurrency.tickerSymbol === get(currency).tickerSymbol) {
    return;
  }

  await update({ mainCurrency: newCurrency.tickerSymbol });
};

const { start, stop, isPending } = useTimeoutFn(
  () => {
    set(filter, '');
  },
  400,
  { immediate: false }
);

const selectFirst = async () => {
  const currencies = get(filteredCurrencies);
  if (currencies.length === 0) {
    return;
  }
  await onSelected(currencies[0]);
  if (get(isPending)) {
    stop();
  }
  start();
};

const calculateFontSize = (symbol: string) => {
  const length = symbol.length;
  return `${2.4 - length * 0.4}em`;
};
</script>

<template>
  <div>
    <VMenu
      v-model="visible"
      transition="slide-y-transition"
      max-width="350px"
      min-width="350px"
      offset-y
      :close-on-content-click="false"
    >
      <template #activator="{ on }">
        <MenuTooltipButton
          :tooltip="
            t('currency_drop_down.profit_currency', {
              currency: currency.tickerSymbol
            })
          "
          class-name="secondary--text text--lighten-4"
          :on-menu="on"
        >
          <span class="currency-dropdown">
            {{ currency.unicodeSymbol }}
          </span>
        </MenuTooltipButton>
      </template>
      <div>
        <VRow class="px-4 py-3">
          <VCol>
            <VTextField
              v-model="filter"
              outlined
              dense
              autofocus
              hide-details
              label="Filter"
              prepend-inner-icon="mdi-magnify"
              @keypress.enter="selectFirst()"
            />
          </VCol>
        </VRow>
        <VDivider />
        <VList class="currency-dropdown__list">
          <VListItem
            v-for="item in filteredCurrencies"
            :id="`change-to-${item.tickerSymbol.toLocaleLowerCase()}`"
            :key="item.tickerSymbol"
            @click="onSelected(item)"
          >
            <VListItemAvatar
              class="currency-list primary--text"
              :style="{ fontSize: calculateFontSize(item.unicodeSymbol) }"
            >
              {{ item.unicodeSymbol }}
            </VListItemAvatar>
            <VListItemContent>
              <VListItemTitle>
                {{ item.name }}
              </VListItemTitle>
              <VListItemSubtitle>
                {{ t('currency_drop_down.hint') }}
              </VListItemSubtitle>
            </VListItemContent>
          </VListItem>
        </VList>
      </div>
    </VMenu>
  </div>
</template>

<style scoped lang="scss">
.currency-dropdown {
  font-size: 1.8em !important;
  font-weight: bold !important;

  &__list {
    max-height: 400px;
    overflow-y: scroll;
  }
}

.currency-list {
  font-weight: bold;
}
</style>

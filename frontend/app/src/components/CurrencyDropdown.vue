<template>
  <div>
    <v-menu
      v-model="visible"
      transition="slide-y-transition"
      max-width="350px"
      min-width="350px"
      offset-y
      :close-on-content-click="false"
    >
      <template #activator="{ on }">
        <menu-tooltip-button
          :tooltip="tc('currency_drop_down.profit_currency')"
          class-name="currency-dropdown secondary--text text--lighten-4"
          :on-menu="on"
        >
          {{ currency.unicodeSymbol }}
        </menu-tooltip-button>
      </template>
      <div>
        <v-row class="px-4 py-3">
          <v-col>
            <v-text-field
              v-model="filter"
              outlined
              dense
              autofocus
              hide-details
              label="Filter"
              prepend-inner-icon="mdi-magnify"
              @keypress.enter="selectFirst()"
            />
          </v-col>
        </v-row>
        <v-divider />
        <v-list class="currency-dropdown__list">
          <v-list-item
            v-for="item in filteredCurrencies"
            :id="`change-to-${item.tickerSymbol.toLocaleLowerCase()}`"
            :key="item.tickerSymbol"
            @click="onSelected(item)"
          >
            <v-list-item-avatar
              class="currency-list primary--text"
              :style="{ fontSize: calculateFontSize(item.unicodeSymbol) }"
            >
              {{ item.unicodeSymbol }}
            </v-list-item-avatar>
            <v-list-item-content>
              <v-list-item-title>
                {{ item.name }}
              </v-list-item-title>
              <v-list-item-subtitle>
                {{ tc('currency_drop_down.hint') }}
              </v-list-item-subtitle>
            </v-list-item-content>
          </v-list-item>
        </v-list>
      </div>
    </v-menu>
  </div>
</template>

<script setup lang="ts">
import MenuTooltipButton from '@/components/helper/MenuTooltipButton.vue';
import { useSettingsStore } from '@/store/settings';
import { useGeneralSettingsStore } from '@/store/settings/general';
import { useCurrencies, Currency } from '@/types/currencies';

const { update } = useSettingsStore();
const { currency } = storeToRefs(useGeneralSettingsStore());

const filter = ref<string>('');
const visible = ref<boolean>(false);

const { tc } = useI18n();
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
    return (
      currencyName.indexOf(filterValue) >= 0 || symbol.indexOf(filterValue) >= 0
    );
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

<style scoped lang="scss">
:deep() {
  .currency-dropdown {
    font-size: 1.6em !important;
    font-weight: bold !important;

    &__list {
      max-height: 400px;
      overflow-y: scroll;
    }
  }
}

.currency-list {
  font-weight: bold;
}
</style>

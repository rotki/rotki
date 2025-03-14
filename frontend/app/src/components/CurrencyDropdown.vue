<script setup lang="ts">
import { type Currency, useCurrencies } from '@/types/currencies';
import { useGeneralSettingsStore } from '@/store/settings/general';
import { useSettingsStore } from '@/store/settings';
import ListItem from '@/components/common/ListItem.vue';
import MenuTooltipButton from '@/components/helper/MenuTooltipButton.vue';
import { useCurrencyUpdate } from '@/composables/use-currency-update';

const { update } = useSettingsStore();
const { currency } = storeToRefs(useGeneralSettingsStore());

const filter = ref<string>('');
const visible = ref<boolean>(false);

const { t } = useI18n();
const { currencies } = useCurrencies();
const { onCurrencyUpdate } = useCurrencyUpdate();

const filteredCurrencies = computed<Currency[]>(() => {
  const filterValue = get(filter).toLocaleLowerCase();
  const supportedCurrencies = get(currencies);
  if (!filterValue)
    return supportedCurrencies;

  return supportedCurrencies.filter(({ name, tickerSymbol }) => {
    const currencyName = name.toLocaleLowerCase();
    const symbol = tickerSymbol.toLocaleLowerCase();
    return currencyName.includes(filterValue) || symbol.includes(filterValue);
  });
});

async function onSelected(newCurrency: Currency) {
  set(visible, false);
  if (newCurrency.tickerSymbol === get(currency).tickerSymbol)
    return;

  await update({ mainCurrency: newCurrency.tickerSymbol });
  await onCurrencyUpdate();
}

const { isPending, start, stop } = useTimeoutFn(
  () => {
    set(filter, '');
  },
  400,
  { immediate: false },
);

async function selectFirst() {
  const currencies = get(filteredCurrencies);
  if (currencies.length === 0)
    return;

  await onSelected(currencies[0]);
  if (get(isPending))
    stop();

  start();
}

function calculateFontSize(symbol: string) {
  const length = symbol.length;
  return `${2.4 - length * 0.4}em`;
}

watch(visible, (isVisible, wasVisible) => {
  if (!isVisible && wasVisible) {
    set(filter, '');
  }
});
</script>

<template>
  <RuiMenu
    v-model="visible"
    menu-class="w-[22rem]"
    :popper="{ placement: 'bottom' }"
  >
    <template #activator="{ attrs }">
      <MenuTooltipButton
        :tooltip="
          t('currency_drop_down.profit_currency', {
            currency: currency.tickerSymbol,
          })
        "
        class-name="text-[1.375rem] font-bold"
        data-cy="currency-dropdown"
        v-bind="attrs"
      >
        {{ currency.unicodeSymbol }}
      </MenuTooltipButton>
    </template>
    <div class="border-b border-default p-3">
      <RuiTextField
        v-model="filter"
        variant="outlined"
        dense
        autofocus
        hide-details
        clearable
        color="primary"
        :label="t('common.actions.filter')"
        prepend-inner-icon="mdi-magnify"
        @keyup.enter="selectFirst()"
      />
    </div>
    <div class="max-h-[25rem] overflow-auto">
      <ListItem
        v-for="item in filteredCurrencies"
        :id="`change-to-${item.tickerSymbol.toLocaleLowerCase()}`"
        :key="item.tickerSymbol"
        size="lg"
        :title="item.name"
        :subtitle="t('currency_drop_down.hint')"
        @click="onSelected(item)"
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
    </div>
  </RuiMenu>
</template>

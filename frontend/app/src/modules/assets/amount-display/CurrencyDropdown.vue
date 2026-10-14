<script setup lang="ts">
import { type Currency, useCurrencies } from '@/modules/assets/amount-display/currencies';
import { useCurrencyUpdate } from '@/modules/assets/prices/use-currency-update';
import { useSetting } from '@/modules/settings/use-setting';
import { useSettingsOperations } from '@/modules/settings/use-settings-operations';
import ListItem from '@/modules/shell/components/ListItem.vue';
import MenuTooltipButton from '@/modules/shell/components/MenuTooltipButton.vue';

const { update } = useSettingsOperations();
const currency = useSetting('currency');

const filter = ref<string>('');
const visible = ref<boolean>(false);

const { t } = useI18n({ useScope: 'global' });
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

function calculateFontSize(symbol: string, small = false) {
  const length = symbol.length;
  if (small) {
    return `${1.8 - length * 0.25}em`;
  }
  return `${2.4 - length * 0.4}em`;
}

/** Fits a symbol into the list's 32px tile: one character at 1rem, each further one a step smaller. */
function symbolSize(symbol: string): string {
  return `${Math.max(0.625, 1 - (symbol.length - 1) * 0.2)}rem`;
}

function isCurrent(item: Currency): boolean {
  return item.tickerSymbol === get(currency).tickerSymbol;
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
    :class-names="{ menu: 'w-88' }"
    :options="{ placement: 'bottom' }"
  >
    <template #activator="{ attrs }">
      <MenuTooltipButton
        :tooltip="
          t('currency_drop_down.profit_currency', {
            currency: currency.tickerSymbol,
          })
        "
        class-name="text-[1.375rem] font-bold"
        data-testid="currency-dropdown"
        v-bind="attrs"
        :style="{
          fontSize: calculateFontSize(currency.unicodeSymbol, true),
        }"
      >
        {{ currency.unicodeSymbol }}
      </MenuTooltipButton>
    </template>
    <div class="border-b border-rui-divider p-3">
      <div class="text-sm font-medium text-rui-text mb-2">
        {{ t('currency_drop_down.title') }}
      </div>
      <RuiTextField
        v-model="filter"
        dense
        autofocus
        hide-details
        clearable
        color="primary"
        :label="t('common.actions.filter')"
        label-placement="hidden"
        :placeholder="t('currency_drop_down.search_placeholder')"
        prepend-icon="lu-search"
        @keyup.enter="selectFirst()"
      />
    </div>
    <div class="max-h-100 overflow-auto py-1">
      <ListItem
        v-for="item in filteredCurrencies"
        :id="`change-to-${item.tickerSymbol.toLocaleLowerCase()}`"
        :key="item.tickerSymbol"
        :title="item.name"
        :class="{ 'bg-rui-primary-subtle': isCurrent(item) }"
        :aria-current="isCurrent(item) || undefined"
        @click="onSelected(item)"
      >
        <template #avatar>
          <div
            class="size-8 rounded-rui-sm bg-rui-surface-muted text-rui-text font-semibold flex items-center justify-center"
            :style="{ fontSize: symbolSize(item.unicodeSymbol) }"
          >
            {{ item.unicodeSymbol }}
          </div>
        </template>
        <div class="flex items-center gap-2 min-w-0">
          <span class="text-sm font-medium text-rui-text truncate">{{ item.name }}</span>
          <span class="text-xs text-rui-text-secondary">{{ item.tickerSymbol }}</span>
          <RuiIcon
            v-if="isCurrent(item)"
            name="lu-check"
            size="16"
            class="ms-auto shrink-0 text-rui-primary"
          />
        </div>
      </ListItem>
    </div>
  </RuiMenu>
</template>

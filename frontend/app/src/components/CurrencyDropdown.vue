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
          :tooltip="$t('currency_drop_down.profit_currency')"
          class-name="currency-dropdown secondary--text text--lighten-4"
          :on-menu="on"
        >
          {{ currency.unicodeSymbol }}
        </menu-tooltip-button>
      </template>
      <div>
        <v-row class="ps-4 pe-4">
          <v-col>
            <v-text-field
              v-model="filter"
              autofocus
              label="Filter"
              prepend-icon="mdi-magnify"
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
            <v-list-item-avatar class="currency-list primary--text">
              {{ item.unicodeSymbol }}
            </v-list-item-avatar>
            <v-list-item-content>
              <v-list-item-title>
                {{ item.name }}
              </v-list-item-title>
              <v-list-item-subtitle v-text="$t('currency_drop_down.hint')" />
            </v-list-item-content>
          </v-list-item>
        </v-list>
      </div>
    </v-menu>
  </div>
</template>

<script lang="ts">
import { computed, defineComponent, ref } from '@vue/composition-api';
import { get, set, useTimeoutFn } from '@vueuse/core';
import MenuTooltipButton from '@/components/helper/MenuTooltipButton.vue';
import { setupGeneralSettings, setupSession } from '@/composables/session';
import { currencies } from '@/data/currencies';
import ThemeMixin from '@/mixins/theme-mixin';
import { Currency } from '@/types/currency';

export default defineComponent({
  name: 'CurrencyDropdown',
  components: { MenuTooltipButton },
  mixins: [ThemeMixin],
  setup() {
    const { updateSettings } = setupSession();
    const { currency } = setupGeneralSettings();

    const filter = ref<string>('');
    const visible = ref<boolean>(false);

    const filteredCurrencies = computed<Currency[]>(() => {
      const filterValue = get(filter).toLocaleLowerCase();
      if (!filterValue) {
        return currencies;
      }
      return currencies.filter(({ name, tickerSymbol }) => {
        const currencyName = name.toLocaleLowerCase();
        const symbol = tickerSymbol.toLocaleLowerCase();
        return (
          currencyName.indexOf(filterValue) >= 0 ||
          symbol.indexOf(filterValue) >= 0
        );
      });
    });

    const onSelected = async (newCurrency: Currency) => {
      set(visible, false);
      if (newCurrency.tickerSymbol === get(currency).tickerSymbol) {
        return;
      }

      await updateSettings({ mainCurrency: newCurrency.tickerSymbol });
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

    return {
      filter,
      visible,
      currency,
      selectFirst,
      filteredCurrencies,
      onSelected
    };
  }
});
</script>

<style scoped lang="scss">
::v-deep {
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
  font-size: 2em;
  font-weight: bold;
}
</style>

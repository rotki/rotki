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
          class-name="currency-dropdown secondary--text text--lighten-2"
          :on-menu="on"
        >
          {{ currency.unicodeSymbol }}
        </menu-tooltip-button>
      </template>
      <div :style="backgroundStyle">
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
            v-for="currency in currencies"
            :id="`change-to-${currency.tickerSymbol.toLocaleLowerCase()}`"
            :key="currency.tickerSymbol"
            @click="onSelected(currency)"
          >
            <v-list-item-avatar class="currency-list primary--text">
              {{ currency.unicodeSymbol }}
            </v-list-item-avatar>
            <v-list-item-content>
              <v-list-item-title>
                {{ currency.name }}
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
import { Component, Mixins } from 'vue-property-decorator';
import { mapActions, mapGetters } from 'vuex';
import MenuTooltipButton from '@/components/helper/MenuTooltipButton.vue';
import { currencies } from '@/data/currencies';
import ThemeMixin from '@/mixins/theme-mixin';
import { Currency } from '@/types/currency';
import { SettingsUpdate } from '@/types/user';

@Component({
  components: { MenuTooltipButton },
  computed: mapGetters('session', ['currency']),
  methods: {
    ...mapActions('session', ['updateSettings'])
  }
})
export default class CurrencyDropDown extends Mixins(ThemeMixin) {
  currency!: Currency;
  updateSettings!: (update: SettingsUpdate) => Promise<void>;
  filter: string = '';
  visible: boolean = false;
  pendingTimeout: any = 0;

  get currencies(): Currency[] {
    const filter = this.filter.toLocaleLowerCase();
    if (!filter) {
      return currencies;
    }
    return currencies.filter(({ name, tickerSymbol }) => {
      const currencyName = name.toLocaleLowerCase();
      const symbol = tickerSymbol.toLocaleLowerCase();
      return currencyName.indexOf(filter) >= 0 || symbol.indexOf(filter) >= 0;
    });
  }

  async selectFirst() {
    const currencies = this.currencies;
    if (currencies.length === 0) {
      return;
    }
    await this.onSelected(currencies[0]);
    if (this.pendingTimeout) {
      clearTimeout(this.pendingTimeout);
    }
    this.pendingTimeout = setTimeout(() => (this.filter = ''), 400);
  }

  async onSelected(currency: Currency) {
    this.visible = false;
    if (currency.tickerSymbol === this.currency.tickerSymbol) {
      return;
    }

    await this.updateSettings({ mainCurrency: currency.tickerSymbol });
  }
}
</script>

<style scoped lang="scss">
@import '~@/scss/scroll';

::v-deep {
  .currency-dropdown {
    font-size: 1.6em !important;
    font-weight: bold !important;

    &__list {
      max-height: 400px;
      overflow-y: scroll;

      @extend .themed-scrollbar;
    }
  }
}

.currency-list {
  font-size: 2em;
  font-weight: bold;
}
</style>

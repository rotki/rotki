<template>
  <div>
    <v-menu
      v-model="visible"
      transition="slide-y-transition"
      max-width="350px"
      min-width="350px"
      bottom
      offset-y
      :close-on-content-click="false"
    >
      <template #activator="{ on }">
        <menu-tooltip-button
          :tooltip="$t('currency_drop_down.profit_currency')"
          class-name="currency-dropdown secondary--text text--lighten-2"
          :on-menu="on"
        >
          {{ currency.unicode_symbol }}
        </menu-tooltip-button>
      </template>
      <div class="currency-dropdown__content">
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
            :id="`change-to-${currency.ticker_symbol.toLocaleLowerCase()}`"
            :key="currency.ticker_symbol"
            @click="onSelected(currency)"
          >
            <v-list-item-avatar class="currency-list primary--text">
              {{ currency.unicode_symbol }}
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
import { Component, Vue } from 'vue-property-decorator';
import { mapActions, mapGetters } from 'vuex';
import MenuTooltipButton from '@/components/helper/MenuTooltipButton.vue';
import { currencies } from '@/data/currencies';
import { Currency } from '@/model/currency';
import { SettingsUpdate } from '@/typing/types';

@Component({
  components: { MenuTooltipButton },
  computed: mapGetters('session', ['currency']),
  methods: {
    ...mapActions('session', ['updateSettings'])
  }
})
export default class CurrencyDropDown extends Vue {
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
    return currencies.filter(({ name, ticker_symbol }) => {
      const currencyName = name.toLocaleLowerCase();
      const symbol = ticker_symbol.toLocaleLowerCase();
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
    if (currency.ticker_symbol === this.currency.ticker_symbol) {
      return;
    }

    await this.updateSettings({ main_currency: currency.ticker_symbol });
  }
}
</script>

<style scoped lang="scss">
@import '~@/scss/scroll';

::v-deep {
  .currency-dropdown {
    font-size: 1.6em !important;
    font-weight: bold !important;

    &__content {
      background: white;
    }

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

<template>
  <div>
    <v-menu transition="slide-y-transition" bottom offset-y>
      <template #activator="{ on }">
        <menu-tooltip-button
          tooltip="Profit Currency"
          class-name="currency-dropdown secondary--text text--lighten-2"
          :on-menu="on"
        >
          {{ currency.unicode_symbol }}
        </menu-tooltip-button>
      </template>
      <v-list>
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
            <v-list-item-subtitle>
              Select as the main currency
            </v-list-item-subtitle>
          </v-list-item-content>
        </v-list-item>
      </v-list>
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

  get currencies(): Currency[] {
    return currencies;
  }

  async onSelected(currency: Currency) {
    if (currency.ticker_symbol === this.currency.ticker_symbol) {
      return;
    }

    await this.updateSettings({ main_currency: currency.ticker_symbol });
  }
}
</script>

<style scoped lang="scss">
::v-deep {
  .currency-dropdown {
    font-size: 1.6em !important;
    font-weight: bold !important;
  }
}

.currency-list {
  font-size: 2em;
  font-weight: bold;
}
</style>

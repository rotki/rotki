<template xmlns:v-slot="http://www.w3.org/1999/XSL/Transform">
  <v-menu id="currency-dropdown" transition="slide-y-transition" bottom>
    <template v-slot:activator="{ on }">
      <v-btn color="primary" dark icon flat v-on="on">
        <v-icon id="current-main-currency" class="" :class="currency.icon">
          fa fa-fw {{ currency.icon }}
        </v-icon>
        <v-icon>fa fa-caret-down</v-icon>
      </v-btn>
    </template>
    <v-list>
      <v-list-tile
        v-for="currency in currencies"
        :id="`change-to-${currency.ticker_symbol.toLocaleLowerCase()}`"
        :key="currency.ticker_symbol"
        @click="onSelected(currency)"
      >
        <v-list-tile-avatar>
          <v-icon color="primary">fa {{ currency.icon }} fa-fw</v-icon>
        </v-list-tile-avatar>
        <v-list-tile-content>
          <v-list-tile-title>
            {{ currency.name }}
          </v-list-tile-title>
          <v-list-tile-sub-title>
            Select as the main currency
          </v-list-tile-sub-title>
        </v-list-tile-content>
      </v-list-tile>
    </v-list>
  </v-menu>
</template>

<script lang="ts">
import { Component, Vue } from 'vue-property-decorator';
import { Currency } from '@/model/currency';
import { settings } from '@/legacy/settings';
import { showError } from '@/legacy/utils';
import { currencies } from '@/data/currencies';
import { mapState } from 'vuex';

@Component({
  computed: mapState(['currency'])
})
export default class CurrencyDropDown extends Vue {
  currency!: Currency;

  get currencies(): Currency[] {
    return currencies;
  }

  onSelected(currency: Currency) {
    if (currency.ticker_symbol === settings.main_currency.ticker_symbol) {
      return;
    }

    this.$rpc
      .set_main_currency(currency)
      .then(value => {
        this.$store.commit('defaultCurrency', value);
      })
      .catch((reason: Error) => {
        showError('Error', `Error at setting main currency: ${reason.message}`);
      });
  }
}
</script>

<style scoped></style>

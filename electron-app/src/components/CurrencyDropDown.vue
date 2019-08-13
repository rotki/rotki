<template>
  <v-menu id="currency-dropdown" transition="slide-y-transition" bottom>
    <template #activator="{ on }">
      <v-btn color="primary" dark icon text v-on="on">
        <v-icon id="current-main-currency" class="" :class="currency.icon">
          fa fa-fw {{ currency.icon }}
        </v-icon>
        <v-icon>fa fa-caret-down</v-icon>
      </v-btn>
    </template>
    <v-list>
      <v-list-item
        v-for="currency in currencies"
        :id="`change-to-${currency.ticker_symbol.toLocaleLowerCase()}`"
        :key="currency.ticker_symbol"
        @click="onSelected(currency)"
      >
        <v-list-item-avatar>
          <v-icon color="primary">fa {{ currency.icon }} fa-fw</v-icon>
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
</template>

<script lang="ts">
import { Component, Vue } from 'vue-property-decorator';
import { Currency } from '@/model/currency';
import { currencies } from '@/data/currencies';
import { createNamespacedHelpers } from 'vuex';

const { mapState } = createNamespacedHelpers('session');

@Component({
  computed: mapState(['currency'])
})
export default class CurrencyDropDown extends Vue {
  currency!: Currency;

  get currencies(): Currency[] {
    return currencies;
  }

  onSelected(currency: Currency) {
    if (currency.ticker_symbol === this.$store.state.currency.ticker_symbol) {
      return;
    }

    this.$rpc
      .set_main_currency(currency)
      .then(value => {
        this.$store.commit('defaultCurrency', value);
      })
      .catch((reason: Error) => {
        //showError('Error', `Error at setting main currency: ${reason.message}`);
      });
  }
}
</script>

<style scoped></style>

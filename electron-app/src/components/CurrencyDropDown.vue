<template>
  <v-menu transition="slide-y-transition" bottom>
    <template #activator="{ on }">
      <v-btn class="currency-dropdown" color="primary" dark icon text v-on="on">
        {{ currency.unicode_symbol }}
      </v-btn>
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
</template>

<script lang="ts">
import { Component, Vue } from 'vue-property-decorator';
import { Currency } from '@/model/currency';
import { currencies } from '@/data/currencies';
import { createNamespacedHelpers } from 'vuex';
import { Message } from '@/store/store';

const { mapGetters } = createNamespacedHelpers('session');

@Component({
  computed: mapGetters(['currency'])
})
export default class CurrencyDropDown extends Vue {
  currency!: Currency;

  get currencies(): Currency[] {
    return currencies;
  }

  onSelected(currency: Currency) {
    if (currency.ticker_symbol === this.currency.ticker_symbol) {
      return;
    }

    this.$api
      .setMainCurrency(currency)
      .then(() => {
        this.$store.commit('session/defaultCurrency', currency);
      })
      .catch((reason: Error) => {
        this.$store.commit('setMessage', {
          title: 'Error',
          description: `Setting the main currency was not successful: ${reason.message}`,
          success: false
        } as Message);
      });
  }
}
</script>

<style scoped lang="scss">
.currency-dropdown {
  font-size: 1.6em;
  font-weight: bold;
}
.currency-list {
  font-size: 2em;
  font-weight: bold;
}
</style>

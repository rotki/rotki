<template>
  <li class="dropdown">
    <a
      class="dropdown-toggle"
      data-toggle="dropdown"
      href="#"
      aria-expanded="false"
    >
      <i id="current-main-currency" class="fa fa-fw" :class="currency.icon"></i>
      <i class="fa fa-caret-down"></i>
    </a>
    <ul class="dropdown-menu currency-dropdown">
      <li v-for="currency in currencies" @click="onSelected(currency)">
        <a
          :id="`change-to-${currency.ticker_symbol.toLocaleLowerCase()}`"
          href="#"
        >
          <div>
            <i class="fa fa-fw" :class="currency.icon"></i>
            Set {{ currency.name }} as the main currency
          </div>
        </a>
      </li>
      <li class="divider"></li>
    </ul>
  </li>
</template>

<script lang="ts">
import { Component, Vue } from 'vue-property-decorator';
import { Currency } from '@/model/currency';
import { settings } from '@/legacy/settings';
import { showError } from '@/legacy/utils';
import { currencies } from '@/data/currencies';
import { set_ui_main_currency } from '@/legacy/topmenu';
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
        settings.main_currency = value;
        set_ui_main_currency(value);
      })
      .catch((reason: Error) => {
        showError('Error', `Error at setting main currency: ${reason.message}`);
      });
  }
}
</script>

<style scoped></style>

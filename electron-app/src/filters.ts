import Vue from 'vue';
import { displayDateFormatter } from '@/data/date_formatter';
import BigNumber from 'bignumber.js';
import { bigNumberify, Zero } from '@/utils/bignumbers';
import { AccountBalance } from '@/model/blockchain-balances';

function percentage(value: string, total: string, precision: number): string {
  const percentage = parseFloat(value) / parseFloat(total);
  return (percentage * 100).toFixed(precision);
}

function precision(value: number, precision: number): string {
  return value.toFixed(precision);
}

function formatDate(value: number, format: string): string {
  return displayDateFormatter.format(new Date(value * 1000), format);
}

function formatPrice(value: BigNumber, precision: number) {
  return value.toFormat(precision);
}

function calculatePrice(value: BigNumber, exchangeRate: number): BigNumber {
  return value.multipliedBy(bigNumberify(exchangeRate));
}

function balanceSum(value: BigNumber[], amount: boolean): BigNumber {
  return value.reduce(
    (previousValue, currentValue) => previousValue.plus(currentValue),
    Zero
  );
}

Vue.filter('percentage', percentage);
Vue.filter('precision', precision);
Vue.filter('formatDate', formatDate);
Vue.filter('formatPrice', formatPrice);
Vue.filter('calculatePrice', calculatePrice);
Vue.filter('balanceSum', balanceSum);

import Vue from 'vue';
import { displayDateFormatter } from '@/data/date_formatter';
import BigNumber from 'bignumber.js';

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
  return value.toPrecision(precision);
}

Vue.filter('percentage', percentage);
Vue.filter('precision', precision);
Vue.filter('formatDate', formatDate);
Vue.filter('formatPrice', formatPrice);

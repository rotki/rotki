import Vue from 'vue';

function percentage(value: string, total: string, precision: number): string {
  const percentage = parseFloat(value) / parseFloat(total);
  return (percentage * 100).toFixed(precision);
}

function precision(value: number, precision: number): string {
  return value.toFixed(precision);
}

Vue.filter('percentage', percentage);
Vue.filter('precision', precision);

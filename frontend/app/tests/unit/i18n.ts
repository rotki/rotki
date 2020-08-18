import Vue from 'vue';

function I18n(vue: typeof Vue): void {
  vue.prototype.$t = (key: string) => key;
}

Vue.use(I18n);

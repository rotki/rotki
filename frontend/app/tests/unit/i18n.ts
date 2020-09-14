import Vue from 'vue';

function stringify(value: { [key: string]: any }): string {
  return Object.values(value)
    .map(value => value.toString())
    .join(', ');
}

function I18n(vue: typeof Vue): void {
  vue.prototype.$t = (key: string, args?: object) =>
    args ? `${key}::${stringify(args)}` : key;
  vue.prototype.$tc = (key: string, choice?: number, args?: object) =>
    args ? `${key}::${choice}::${stringify(args)}` : key;
}

Vue.use(I18n);

import Vue from 'vue';

function stringify(value: { [key: string]: any }): string {
  return Object.values(value)
    .map(value => value.toString())
    .join(', ');
}

export const mockT = (key: any, args?: any) =>
  args ? `${key}::${stringify(args)}` : key;

function I18n(vue: typeof Vue): void {
  vue.prototype.$t = mockT;
  vue.prototype.$tc = (key: string, choice?: number, args?: object) =>
    args ? `${key}::${choice}::${stringify(args)}` : key;
}

Vue.use(I18n);

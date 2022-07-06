vi.mock('@/i18n');

import Vue from 'vue';

function stringify(value: { [key: string]: any }): string {
  return Object.values(value)
    .map(value => value.toString())
    .join(', ');
}

const mockT = (key: any, args?: any) =>
  args ? `${key}::${stringify(args)}` : key;

const mockTc = (key: string, choice?: number, args?: object) =>
  args ? `${key}::${choice}::${stringify(args)}` : key;

export const I18n = (vue: typeof Vue) => {
  vue.prototype.$t = mockT;
  vue.prototype.$tc = mockTc;
};

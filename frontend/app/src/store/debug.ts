import { BigNumber } from '@rotki/common';
import createPersistedState from 'vuex-persistedstate';
import { bigNumberify } from '@/utils/bignumbers';

function convert(data: any): any {
  if (Array.isArray(data)) {
    return data.map(entry => convert(entry));
  }

  if (!isObject(data)) {
    return data;
  }

  const converted: { [key: string]: any } = {};
  Object.keys(data).map(key => {
    let datum = data[key];
    if (datum instanceof BigNumber) {
      datum = `bn::${datum.toString()}`;
    }

    converted[key] = isObject(datum) ? convert(datum) : datum;
  });

  return converted;
}

const isObject = (data: any): boolean =>
  typeof data === 'object' &&
  data !== null &&
  !(data instanceof RegExp) &&
  !(data instanceof Error) &&
  !(data instanceof Date);

export const storePlugins = () => {
  const debugSettings = window.interop?.debugSettings?.();
  const persistVuex = debugSettings?.vuex || process.env.VUE_APP_PERSIST_VUEX;

  if (!persistVuex) {
    sessionStorage.removeItem('vuex');
  }

  return persistVuex
    ? [
        createPersistedState({
          storage: sessionStorage,
          getState: (key, storage) => {
            return JSON.parse(storage.getItem(key), (key1, value) => {
              if (typeof value === 'string' && value.startsWith('bn::')) {
                return bigNumberify(value.replace('bn::', ''));
              }
              return value;
            });
          },
          setState: (key, state, storage) => {
            storage.setItem(key, JSON.stringify(convert(state)));
          }
        })
      ]
    : [];
};

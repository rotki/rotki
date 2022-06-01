import { BigNumber } from '@rotki/common';
import { PiniaPluginContext } from 'pinia';
import createPersistedState from 'vuex-persistedstate';
import { bigNumberify } from '@/utils/bignumbers';
import { logger } from '@/utils/logging';

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

const storage = sessionStorage;

const getState = (key: string) => {
  const items = storage.getItem(key);
  if (!items) return null;

  return JSON.parse(items, (key1, value) => {
    if (typeof value === 'string' && value.startsWith('bn::')) {
      return bigNumberify(value.replace('bn::', ''));
    }
    return value;
  });
};

const setState = (key: string, state: any) => {
  storage.setItem(key, JSON.stringify(convert(state)));
};

export const storeVuexPlugins = () => {
  const debugSettings = window.interop?.debugSettings?.();
  const persistStore =
    debugSettings?.persistStore || import.meta.env.VITE_PERSIST_STORE;

  if (!persistStore) {
    storage.removeItem('vuex');
    return [];
  }

  return [
    createPersistedState({
      getState,
      setState
    })
  ];
};

export const storePiniaPlugins = (context: PiniaPluginContext) => {
  const debugSettings = window.interop?.debugSettings?.();
  const persistStore =
    debugSettings?.persistStore || import.meta.env.VITE_PERSIST_STORE;

  const { store } = context;
  const storeId = store.$id;

  if (!persistStore) {
    storage.removeItem(storeId);
    return undefined;
  }

  try {
    const fromStorage = getState(storeId);
    if (fromStorage) {
      store.$patch(fromStorage);
    }
  } catch (e) {
    logger.error(e);
  }

  store.$subscribe(
    (_, state) => {
      try {
        setState(storeId, state);
      } catch (e) {
        logger.error(e);
      }
    },
    { detached: true }
  );
};

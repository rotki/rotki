import { createPinia, defineStore, setActivePinia } from 'pinia';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { createApp } from 'vue';
import { StoreStatePersistsPlugin } from './store-debug-plugin';

interface Currency {
  tickerSymbol: string;
}

/** Stands in for the currencies list: one object the app hands to stores and reads elsewhere too. */
const usd: Currency = { tickerSymbol: 'USD' };

const useSettingsLikeStore = defineStore('persist-spec', () => {
  const general = ref<{ mainCurrency: Currency }>({ mainCurrency: usd });
  return { general };
});

function createStore(): ReturnType<typeof useSettingsLikeStore> {
  const pinia = createPinia();
  pinia.use(StoreStatePersistsPlugin);
  createApp({}).use(pinia);
  setActivePinia(pinia);
  return useSettingsLikeStore();
}

describe('storeStatePersistsPlugin', () => {
  beforeEach(() => {
    usd.tickerSymbol = 'USD';
    sessionStorage.clear();
    vi.stubEnv('VITE_PERSIST_STORE', 'true');
    vi.stubEnv('VITE_TEST', '');
  });

  afterEach(() => {
    vi.unstubAllEnvs();
  });

  it('should restore the persisted state of a store', () => {
    sessionStorage.setItem('pinia.store.persist-spec', JSON.stringify({ general: { mainCurrency: { tickerSymbol: 'EUR' } } }));

    const store = createStore();

    expect(store.general.mainCurrency.tickerSymbol).toBe('EUR');
  });

  it('should replace what the state held rather than write the persisted values into it', () => {
    sessionStorage.setItem('pinia.store.persist-spec', JSON.stringify({ general: { mainCurrency: { tickerSymbol: 'EUR' } } }));

    createStore();

    expect(usd.tickerSymbol).toBe('USD');
  });
});

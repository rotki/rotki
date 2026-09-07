import { createCustomPinia } from '@test/utils/create-pinia';
import { createPinia, defineStore, setActivePinia } from 'pinia';
import { describe, expect, it } from 'vitest';

const useCounterStore = defineStore('harness-counter', () => {
  const count = ref<number>(0);

  function increment(): void {
    set(count, get(count) + 1);
  }

  return { count, increment };
});

describe('createCustomPinia', () => {
  it('should apply StoreResetPlugin without the spec mounting anything', () => {
    setActivePinia(createCustomPinia());
    const store = useCounterStore();
    store.increment();
    expect(store.count).toBe(1);

    store.$reset();

    expect(store.count).toBe(0);
  });

  it('should still reset after a mount installs the same pinia into another app', () => {
    const pinia = createCustomPinia();
    createApp({}).use(pinia);
    setActivePinia(pinia);
    const store = useCounterStore();
    store.increment();

    store.$reset();

    expect(store.count).toBe(0);
  });

  it('should be the reason for existing: a bare pinia leaves $reset unimplemented', () => {
    setActivePinia(createPinia());
    const store = useCounterStore();

    expect(() => store.$reset()).toThrow(/setup syntax/);
  });
});

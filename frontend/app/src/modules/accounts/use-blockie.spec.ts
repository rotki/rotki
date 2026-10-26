import type { EffectScope } from 'vue';
import { createBlockie } from '@rotki/ui-library';
import { createCustomPinia } from '@test/utils/create-pinia';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { useBlockie } from '@/modules/accounts/use-blockie';

describe('useBlockie', () => {
  let cache: ReturnType<typeof useBlockie>['cache'];
  let getBlockie: ReturnType<typeof useBlockie>['getBlockie'];
  let scope: EffectScope;
  const address = '0x790b4086d106eafd913e71843aed987efe291c92';

  beforeEach(() => {
    setActivePinia(createCustomPinia());
    vi.clearAllMocks();
    scope = effectScope();
    scope.run(() => {
      ({ cache, getBlockie } = useBlockie());
    });
  });

  afterEach(() => {
    scope.stop();
  });

  it('should create a new blockie for an address', () => {
    getBlockie(address);
    expect(createBlockie).toHaveBeenCalledOnce();
  });

  it('should reuse the cached blockie for the same address regardless of case', () => {
    const first = getBlockie(address);
    vi.mocked(createBlockie).mockClear();

    const second = getBlockie(address.toUpperCase());

    expect(createBlockie).not.toHaveBeenCalled();
    expect(second).toEqual(first);
  });

  it('should draw each blockie of a 500-token list once, however often the list renders', () => {
    const tokens = Array.from({ length: 500 }, (_, index) => `0x${index.toString(16).padStart(40, '0')}`);

    tokens.forEach(token => getBlockie(token));
    tokens.forEach(token => getBlockie(token));

    expect(createBlockie).toHaveBeenCalledTimes(500);
  });

  it('should evict the least recently used entry once the cache limit is reached', () => {
    getBlockie('0xkept');
    getBlockie(address);
    expect(cache.size).toBe(2);

    for (let i = 0; i < 998; i++) getBlockie(i.toString());
    getBlockie('0xkept');
    getBlockie('overflow');

    expect(cache.size).toBe(1000);
    expect(cache.has(address)).toBe(false);
    expect(cache.has('0xkept')).toBe(true);
  });
});

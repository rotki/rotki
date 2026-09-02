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

  it('should evict the oldest entry once the cache limit is reached', () => {
    getBlockie(address);
    expect(cache.size).toBe(1);
    expect(cache.has(address)).toBe(true);

    for (let i = 0; i < 100; i++) getBlockie(i.toString());

    expect(cache.size).toBe(100);
    expect(cache.has(address)).toBe(false);
  });
});

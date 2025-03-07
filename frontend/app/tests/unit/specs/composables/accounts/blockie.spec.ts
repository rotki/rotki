import { useBlockie } from '@/composables/accounts/blockie';
import { createBlockie } from '@/utils/blockie';
import { createPinia, setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it, vi } from 'vitest';

describe('composables::accounts/blockie', () => {
  setActivePinia(createPinia());
  const { cache, getBlockie } = useBlockie();
  let firstBlockie = '';
  const address = '0x790b4086d106eafd913e71843aed987efe291c92';

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should create new blockie', () => {
    firstBlockie = getBlockie(address);
    expect(createBlockie).toHaveBeenCalled();
  });

  it('should not create new blockie', () => {
    const addressInUppercase = '0x790B4086D106EAFD913E71843AED987EFE291C92';
    const newBlockie = getBlockie(addressInUppercase);
    expect(createBlockie).not.toHaveBeenCalled();
    expect(firstBlockie).toEqual(newBlockie);
  });

  it('should stop caching blockie after cache limit is reached', () => {
    expect(cache.size).toEqual(1);
    expect(cache.has(address)).toBeTruthy();
    for (let i = 0; i < 100; i++) getBlockie(i.toString());

    expect(cache.size).toEqual(100);
    expect(cache.has(address)).toBeFalsy();
  });
});

import { createCustomPinia } from '@test/utils/create-pinia';
import { setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it } from 'vitest';
import { ref } from 'vue';
import { airdropParams, isAirdropStatus, useAirdropFields } from '@/modules/airdrops/use-airdrop-fields';

describe('useAirdropFields', () => {
  beforeEach(() => {
    setActivePinia(createCustomPinia());
  });

  it('should offer the account and status fields', () => {
    expect(useAirdropFields([]).map(field => field.key)).toStrictEqual(['account', 'status']);
  });

  it('should offer only the addresses that have an airdrop', () => {
    const eligible = ref<string[]>(['0xabc']);
    const [account] = useAirdropFields(eligible);
    // The account resolvers come from every tracked account; only the offered list is narrowed,
    // and with no tracked accounts in this pinia nothing survives the narrowing.
    expect(account.suggest?.()).toStrictEqual([]);
  });

  it('should offer every status except all', () => {
    const [, status] = useAirdropFields([]);
    expect(status.suggest?.()).toStrictEqual(['unknown', 'unclaimed', 'claimed', 'missed']);
  });

  it('should keep the status single-valued', () => {
    const [, status] = useAirdropFields([]);
    expect(status.multiple).toBe(false);
  });
});

describe('isAirdropStatus', () => {
  it('should admit a status the page knows', () => {
    expect(isAirdropStatus('claimed')).toBe(true);
  });

  it('should reject anything else, including the old all option', () => {
    expect(isAirdropStatus('all')).toBe(false);
    expect(isAirdropStatus('')).toBe(false);
  });
});

/** The page's two refs are what the bar writes through; absence is what "all" means. */
describe('airdropParams', () => {
  it('should draw no status pill while the ref is empty', () => {
    const params = airdropParams(ref<string[]>([]), ref<string>(''));
    expect(params.value).toStrictEqual({});
  });

  it('should draw both pills from the refs', () => {
    const params = airdropParams(ref<string[]>(['0xabc']), ref<string>('claimed'));
    expect(params.value).toStrictEqual({ addresses: ['0xabc'], status: 'claimed' });
  });

  it('should write the refs from the bag', () => {
    const addresses = ref<string[]>([]);
    const status = ref<string>('');
    const params = airdropParams(addresses, status);

    params.value = { addresses: ['0xabc'], status: 'missed' };

    expect(addresses.value).toStrictEqual(['0xabc']);
    expect(status.value).toBe('missed');
  });

  it('should refuse a status the url invented', () => {
    const status = ref<string>('');
    const params = airdropParams(ref<string[]>([]), status);

    params.value = { status: 'nonsense' };

    expect(status.value).toBe('');
  });
});

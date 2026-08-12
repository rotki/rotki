import { describe, expect, it } from 'vitest';
import { addressBookChainParams } from '@/modules/accounts/address-book/use-address-book-filter';

function setup(chainValue?: string, strictValue = false): {
  chain: Ref<string | undefined>;
  strict: Ref<boolean>;
  params: ReturnType<typeof addressBookChainParams>;
} {
  const chain = ref<string | undefined>(chainValue);
  const strict = ref<boolean>(strictValue);
  return { chain, params: addressBookChainParams(chain, strict), strict };
}

describe('addressBookChainParams', () => {
  // The bug this pair had: both keys were written to the url and neither was ever read back, so a
  // shared link opened the table unfiltered and then rewrote the link to say so.
  it('should restore both keys from the url', () => {
    const { chain, params, strict } = setup();

    params.source.fromQuery?.({ blockchain: 'eth', strictBlockchain: 'true' });

    expect(get(chain)).toBe('eth');
    expect(get(strict)).toBe(true);
  });

  it('should clear both when the url carries neither', () => {
    const { chain, params, strict } = setup('eth', true);

    params.source.fromQuery?.({});

    expect(get(chain)).toBeUndefined();
    expect(get(strict)).toBe(false);
  });

  it('should send both to the request', () => {
    const { params } = setup('eth', true);

    expect(toValue(params.source.values)).toStrictEqual({ blockchain: 'eth', strictBlockchain: true });
  });

  // No chain picked is `undefined` rather than an empty string: that is what the table reads as
  // "every chain", and the request must not carry a blank one.
  it('should leave an unpicked chain undefined', () => {
    const { params } = setup();

    expect(toValue(params.source.values)).toStrictEqual({
      blockchain: undefined,
      strictBlockchain: false,
    });
  });

  it('should draw a pill only for what is set', () => {
    expect(get(setup().params.pillParams)).toStrictEqual({});
    expect(get(setup('eth').params.pillParams)).toStrictEqual({ blockchain: 'eth' });
    expect(get(setup('eth', true).params.pillParams)).toStrictEqual({
      blockchain: 'eth',
      strictBlockchain: true,
    });
  });

  it('should write the refs back from the bar\'s bag', () => {
    const { chain, params, strict } = setup();

    set(params.pillParams, { blockchain: 'optimism', strictBlockchain: true });
    expect(get(chain)).toBe('optimism');
    expect(get(strict)).toBe(true);

    set(params.pillParams, {});
    expect(get(chain)).toBeUndefined();
    expect(get(strict)).toBe(false);
  });

  it('should ride both the request and the url', () => {
    expect(setup().params.source.to).toBe('both');
  });
});

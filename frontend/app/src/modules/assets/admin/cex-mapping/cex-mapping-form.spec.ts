import { describe, expect, it } from 'vitest';
import { cexMappingSchema } from '@/modules/assets/admin/cex-mapping/cex-mapping-form';

const messages = {
  asset: 'asset_missing',
  location: 'location_missing',
  locationSymbol: 'symbol_missing',
};

const valid = {
  asset: 'eip155:1/erc20:0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48',
  location: 'kraken',
  locationSymbol: 'USDC',
};

function messagesFor(state: Record<string, unknown>, forAllExchanges = false): string[] {
  const result = cexMappingSchema(messages, forAllExchanges).safeParse(state);
  if (result.success)
    return [];
  return result.error.issues.map(issue => issue.message);
}

describe('cexMappingSchema', () => {
  it('should accept a mapping tied to one exchange', () => {
    expect(messagesFor(valid)).toEqual([]);
  });

  it.each([
    [null],
    [''],
    ['  '],
  ])('should report %s as a missing exchange for a single-exchange mapping', (location) => {
    expect(messagesFor({ ...valid, location })).toEqual(['location_missing']);
  });

  it('should accept a missing exchange when the mapping covers all of them', () => {
    expect(messagesFor({ ...valid, location: null }, true)).toEqual([]);
  });

  it.each([
    [false],
    [true],
  ])('should require the asset and the symbol with the switch %s', (forAllExchanges) => {
    expect(messagesFor({ ...valid, asset: '', locationSymbol: '' }, forAllExchanges)).toEqual([
      'asset_missing',
      'symbol_missing',
    ]);
  });

  it('should keep an exchange the caller left set even when it covers all of them', () => {
    const result = cexMappingSchema(messages, true).safeParse(valid);

    // The switch does not clear the field, so the payload keeps whatever was chosen before it was
    // flipped. What the api does with that is the dialog's business, not the schema's.
    expect(result.success && result.data).toEqual(valid);
  });
});

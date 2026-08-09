import type { SharedFieldResolvers } from '@/modules/core/table/filters/shared/use-shared-field-resolvers';
import { describe, expect, it } from 'vitest';
import {
  toAddressBookChainField,
  toAddressBookFields,
  toAddressBookStrictField,
} from '@/modules/accounts/address-book/address-book-fields';
import { DisplayKinds } from '@/modules/core/table/pill/core/types';

const t = (key: string): string => key;

const resolvers: SharedFieldResolvers = {
  formatDate: (value: string): string => value,
  parseDate: (): string | undefined => undefined,
  resolveAssetChain: (): string | undefined => undefined,
  resolveAssetSymbol: (value: string): string => value,
  resolveChainName: (): string => 'Optimism',
  resolveHex: (): string => '0x9531...1306',
  resolveLocationName: (value: string): string => value,
  resolveProtocolName: (value: string): string => value,
  resolveTokenName: (value: string): string => value,
};

describe('toAddressBookFields', () => {
  it('should keep the wire keys the table already sends', () => {
    expect(toAddressBookFields(resolvers, t).map(field => field.key)).toStrictEqual([
      'nameSubstring',
      'address',
    ]);
  });

  // Neither has a list to pick from: names are whatever the user wrote, and the book holds
  // arbitrary addresses rather than tracked ones.
  it('should have both values written rather than picked', () => {
    const [name, address] = toAddressBookFields(resolvers, t);

    expect(name.freeText).toBe(true);
    expect(address.freeText).toBe(true);
  });

  it('should draw an address with its avatar, shortened', () => {
    const [, address] = toAddressBookFields(resolvers, t);

    expect(address.display).toBe(DisplayKinds.ADDRESS);
    expect(address.resolveLabel?.('0x9531C059098e3d194fF87FebB587aB07B30B1306')).toBe('0x9531...1306');
    expect(address.multiple).toBe(true);
  });
});

describe('toAddressBookChainField', () => {
  it('should bind the chain to the blockchain param the table already sends', () => {
    expect(toAddressBookChainField(t, resolvers, () => ['optimism'])).toMatchObject({
      binding: { kind: 'param', paramKey: 'blockchain', to: 'both' },
      key: 'blockchain',
      // The backend takes one chain, so the pill offers one.
      multiple: false,
    });
  });

  it('should draw a chain with its logo and display name', () => {
    const field = toAddressBookChainField(t, resolvers, () => ['optimism']);

    expect(field.display).toBe(DisplayKinds.CHAIN);
    expect(field.resolveLabel?.('optimism')).toBe('Optimism');
    expect(field.suggest?.()).toStrictEqual(['optimism']);
  });
});

describe('toAddressBookStrictField', () => {
  // A boolean pill has no editor and no value segment: adding it turns the filter on.
  it('should bind the strict toggle to its param as a boolean', () => {
    expect(toAddressBookStrictField(t)).toMatchObject({
      binding: { kind: 'param', paramKey: 'strictBlockchain', to: 'both' },
      key: 'strictBlockchain',
      multiple: false,
      valueType: 'boolean',
    });
  });

  it('should carry the explanation the checkbox used to show', () => {
    expect(toAddressBookStrictField(t).hint).toBe('address_book.strict_blockchain_filter.hint');
  });
});

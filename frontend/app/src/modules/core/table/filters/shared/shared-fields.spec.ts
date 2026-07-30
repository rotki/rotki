import type { SharedFieldResolvers } from '@/modules/core/table/filters/shared/use-shared-field-resolvers';
import type { FieldDef } from '@/modules/core/table/pill/core/types';
import { describe, expect, it } from 'vitest';
import { decorateSharedField, SharedFieldKinds } from '@/modules/core/table/filters/shared/shared-fields';

const resolvers: SharedFieldResolvers = {
  formatDate: (value: string): string => `date:${value}`,
  parseDate: (value: string): string | undefined => `ts:${value}`,
  resolveAssetChain: (value: string): string | undefined => (value.startsWith('eip155:8453') ? 'base' : undefined),
  resolveAssetSymbol: (value: string): string => `symbol:${value}`,
  resolveHex: (value: string): string => `short:${value}`,
  resolveLocationName: (value: string): string => `location:${value}`,
  resolveProtocolName: (value: string): string => `protocol:${value}`,
  resolveTokenName: (value: string): string => `token:${value}`,
};

function field(overrides: Partial<FieldDef> = {}): FieldDef {
  return {
    allowExclusion: false,
    binding: { kind: 'matcher' },
    key: 'k',
    label: 'K',
    multiple: true,
    operators: ['is'],
    valueType: 'enum',
    ...overrides,
  };
}

describe('decorateSharedField', () => {
  it('should give an asset its icon, symbol and chain', () => {
    const decorated = decorateSharedField(field(), SharedFieldKinds.ASSET, resolvers);

    expect(decorated.display).toBe('asset');
    expect(decorated.resolveLabel?.('eip155:1/erc20:0xA0b8')).toBe('symbol:eip155:1/erc20:0xA0b8');
    expect(decorated.resolveChain?.('eip155:8453/erc20:0x1')).toBe('base');
  });

  it('should give a location and a protocol their own icons and names', () => {
    expect(decorateSharedField(field(), SharedFieldKinds.LOCATION, resolvers)).toMatchObject({ display: 'location' });
    expect(decorateSharedField(field(), SharedFieldKinds.PROTOCOL, resolvers)).toMatchObject({ display: 'counterparty' });
    expect(decorateSharedField(field(), SharedFieldKinds.LOCATION, resolvers).resolveLabel?.('kraken')).toBe('location:kraken');
  });

  // Both are hex and both are shortened, but only an address is an identity worth a face.
  it('should tell an address apart from a transaction hash', () => {
    const address = decorateSharedField(field(), SharedFieldKinds.ADDRESS, resolvers);
    const txHash = decorateSharedField(field(), SharedFieldKinds.TX_HASH, resolvers);

    expect(address).toMatchObject({ display: 'address', freeText: true });
    expect(txHash.display).toBeUndefined();
    expect(txHash.freeText).toBe(true);
    expect(txHash.resolveLabel?.('0xabc')).toBe('short:0xabc');
  });

  // What a value means to the backend stays with the table's matcher: history's transaction filter
  // accepts a signature as well as a hash, which no shape check here would know about.
  it('should leave validation to the field it decorates', () => {
    const validate = (value: string): boolean => value === 'only-this';
    const decorated = decorateSharedField(field({ validate }), SharedFieldKinds.ADDRESS, resolvers);

    expect(decorated.validate).toBe(validate);
  });

  it('should keep the key, operators and binding the table declared', () => {
    const original = field({ key: 'counterparties', multiple: true, operators: ['is', 'is_not'] });

    const decorated = decorateSharedField(original, SharedFieldKinds.PROTOCOL, resolvers);

    expect(decorated).toMatchObject({ binding: { kind: 'matcher' }, key: 'counterparties', operators: ['is', 'is_not'] });
  });

  it('should leave a field that is nobody else\'s kind untouched', () => {
    const original = field({ key: 'assetType' });

    expect(decorateSharedField(original, undefined, resolvers)).toStrictEqual(original);
  });
});

import type { AssetsWithId } from '@/modules/assets/types';
import type { SharedFieldResolvers } from '@/modules/core/table/filters/shared/use-shared-field-resolvers';
import { createMock } from '@test/utils/create-mock';
import { describe, expect, it } from 'vitest';
import { toAssetField } from '@/modules/core/table/filters/shared/asset-field';

const resolvers = createMock<SharedFieldResolvers>({
  resolveAssetChain: (value: string): string | undefined => `chainof:${value}`,
  resolveAssetSymbol: (value: string): string => `symbol:${value}`,
});

const searchAsset = async (): Promise<AssetsWithId> => [];

describe('toAssetField', () => {
  it('should declare a single valued asset field on the table filter bag', () => {
    expect(toAssetField({ key: 'fromAsset', label: 'From', searchAsset }, resolvers)).toMatchObject({
      binding: { kind: 'filter' },
      display: 'asset',
      key: 'fromAsset',
      label: 'From',
      multiple: false,
      valueType: 'asset',
    });
  });

  it('should take more than one asset when the endpoint does', () => {
    expect(toAssetField({ key: 'asset', label: 'Asset', multiple: true, searchAsset }, resolvers).multiple).toBe(true);
  });

  it('should draw an asset by its symbol and chain rather than its identifier', () => {
    const field = toAssetField({ key: 'asset', label: 'Asset', searchAsset }, resolvers);

    expect(field.resolveLabel?.('eip155:1/erc20:0xA0b8')).toBe('symbol:eip155:1/erc20:0xA0b8');
    expect(field.resolveChain?.('eip155:1/erc20:0xA0b8')).toBe('chainof:eip155:1/erc20:0xA0b8');
  });

  it('should be picked through the search, not typed or listed', () => {
    const field = toAssetField({ key: 'asset', label: 'Asset', searchAsset }, resolvers);

    expect(field.searchAsset).toBe(searchAsset);
    expect(field.suggest).toBeUndefined();
    expect(field.freeText).toBeUndefined();
  });

  // The request carries a plain identifier, so there is no form for an excluded asset.
  it('should not offer exclusion', () => {
    const field = toAssetField({ key: 'asset', label: 'Asset', searchAsset }, resolvers);

    expect(field.allowExclusion).toBe(false);
    expect(field.operators).toStrictEqual(['is']);
  });
});

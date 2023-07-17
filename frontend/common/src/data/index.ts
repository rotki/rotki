import { z } from 'zod';
import { Blockchain } from '../blockchain';

export interface ActionResult<T> {
  readonly result: T;
  readonly message: string;
}

export enum EvmTokenKind {
  ERC20 = 'erc20',
  ERC721 = 'erc721'
}

export const EvmTokenKindEnum = z.nativeEnum(EvmTokenKind);

export type EvmTokenKindEnum = z.infer<typeof EvmTokenKindEnum>;

export const UnderlyingToken = z.object({
  address: z.string(),
  tokenKind: EvmTokenKindEnum,
  weight: z.string()
});

export type UnderlyingToken = z.infer<typeof UnderlyingToken>;

export const BaseAsset = z.object({
  identifier: z.string(),
  coingecko: z.string().nullish(),
  cryptocompare: z.string().nullish(),
  started: z.number().nullish(),
  name: z.string().nullish(),
  symbol: z.string().nullish(),
  swappedFor: z.string().nullish(),
  evmChain: z.string().nullish(),
  tokenKind: EvmTokenKindEnum.nullish()
});

export type BaseAsset = z.infer<typeof BaseAsset>;

export const SupportedAsset = BaseAsset.extend({
  active: z.boolean().optional(),
  ended: z.number().nullish(),
  decimals: z.number().nullish(),
  assetType: z.string().nullish(),
  forked: z.string().nullish(),
  address: z.string().nullish(),
  underlyingTokens: z.array(UnderlyingToken).nullish(),
  protocol: z.string().nullish(),
  customAssetType: z.string().nullish()
});

export type SupportedAsset = z.infer<typeof SupportedAsset>;

export const AssetInfo = z.object({
  name: z.string().nullish(),
  symbol: z.string().nullish(),
  evmChain: z.string().nullish(),
  assetType: z.string().nullish(),
  isCustomAsset: z.boolean().nullish(),
  customAssetType: z.string().nullish(),
  collectionId: z.string().nullish(),
  collectionName: z.string().nullish(),
  imageUrl: z.string().nullish()
});

export const AssetInfoWithTransformer = AssetInfo.transform(data => ({
  ...data,
  isCustomAsset: data.isCustomAsset || data.assetType === 'custom asset'
}));

export type AssetInfo = z.infer<typeof AssetInfo>;

export const assetSymbolToIdentifierMap: Record<string, string> = {
  DAI: 'eip155:1/erc20:0x6B175474E89094C44Da98b954EedeAC495271d0F',
  ADX: 'eip155:1/erc20:0xADE00C28244d5CE17D72E40330B1c318cD12B7c3',
  [Blockchain.OPTIMISM]:
    'eip155:10/erc20:0x4200000000000000000000000000000000000042',
  [Blockchain.POLYGON_POS]:
    'eip155:137/erc20:0x0000000000000000000000000000000000001010'
};

export const getIdentifierFromSymbolMap = (symbol: string): string => {
  if (symbol in assetSymbolToIdentifierMap) {
    return assetSymbolToIdentifierMap[symbol];
  }
  return symbol;
};

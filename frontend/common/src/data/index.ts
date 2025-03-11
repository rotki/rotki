import { z } from 'zod';

export interface ActionResult<T> {
  readonly result: T;
  readonly message: string;
}

export enum EvmTokenKind {
  ERC20 = 'erc20',
  ERC721 = 'erc721',
}

const EvmTokenKindEnum = z.nativeEnum(EvmTokenKind);

const UnderlyingToken = z.object({
  address: z.string(),
  tokenKind: EvmTokenKindEnum,
  weight: z.string(),
});

export type UnderlyingToken = z.infer<typeof UnderlyingToken>;

const BaseAsset = z.object({
  coingecko: z.string().nullish(),
  cryptocompare: z.string().nullish(),
  evmChain: z.string().nullish(),
  identifier: z.string(),
  name: z.string().nullish(),
  started: z.number().nullish(),
  swappedFor: z.string().nullish(),
  symbol: z.string().nullish(),
  tokenKind: EvmTokenKindEnum.nullish(),
});

export const SupportedAsset = BaseAsset.extend({
  active: z.boolean().optional(),
  address: z.string().nullish(),
  assetType: z.string().nullish(),
  customAssetType: z.string().nullish(),
  decimals: z.number().nullish(),
  ended: z.number().nullish(),
  forked: z.string().nullish(),
  protocol: z.string().nullish(),
  underlyingTokens: z.array(UnderlyingToken).nullish(),
});

export type SupportedAsset = z.infer<typeof SupportedAsset>;

export const AssetInfo = z.object({
  assetType: z.string().nullish(),
  coingecko: z.string().optional(),
  collectionId: z.string().nullish(),
  collectionName: z.string().nullish(),
  cryptocompare: z.string().optional(),
  customAssetType: z.string().nullish(),
  evmChain: z.string().optional(),
  imageUrl: z.string().nullish(),
  isCustomAsset: z.boolean().nullish(),
  isSpam: z.boolean().optional(),
  mainAsset: z.string().optional(),
  name: z.string().nullish(),
  symbol: z.string().nullish(),
});

export const AssetInfoWithTransformer = AssetInfo.transform(data => ({
  ...data,
  isCustomAsset: data.isCustomAsset || data.assetType === 'custom asset',
}));

export type AssetInfo = z.infer<typeof AssetInfo>;

export const AssetCollection = z.object({
  mainAsset: z.string(),
  name: z.string(),
  symbol: z.string(),
});

export type AssetCollection = z.infer<typeof AssetCollection>;

// note: make sure that the identifier is checksummed
const assetSymbolToIdentifierMap: Record<string, string> = {
  ADX: 'eip155:1/erc20:0xADE00C28244d5CE17D72E40330B1c318cD12B7c3',
  DAI: 'eip155:1/erc20:0x6B175474E89094C44Da98b954EedeAC495271d0F',
};

export function getIdentifierFromSymbolMap(symbol: string): string {
  if (symbol in assetSymbolToIdentifierMap)
    return assetSymbolToIdentifierMap[symbol];

  return symbol;
}

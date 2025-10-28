import { type AssetInfoWithId, NumericString } from '@rotki/common';
import { z } from 'zod/v4';

/**
 * It is like {@link AssetInfoWithId} but with two extra properties for
 * NFTs. It contains an imageUrl (optional) which is the image associated
 * with the NFT and a collectionName (optional)
 */
export interface NftAsset extends AssetInfoWithId {
  imageUrl?: string;
  collectionName?: string;
}

const NftCollectionInfo = z.object({
  bannerImage: z.string().nullable(),
  description: z.string().nullable(),
  largeImage: z.string().nullable(),
  name: z.string().nullable(),
});

const Nft = z.object({
  backgroundColor: z.string().nullable(),
  collection: NftCollectionInfo,
  externalLink: z
    .string()
    .nullable()
    .transform(item => item || undefined),
  imageUrl: z.string().nullable(),
  name: z.string().nullable(),
  permalink: z.string().nullable(),
  priceAsset: z.string(),
  priceInAsset: NumericString,
  priceUsd: NumericString,
  tokenIdentifier: z.string().min(1),
});

export type Nft = z.infer<typeof Nft>;

export interface GalleryNft extends Nft {
  address: string;
}

const Nfts = z.record(z.string(), z.array(Nft));

export type Nfts = z.infer<typeof Nfts>;

export const NftResponse = z.object({
  addresses: Nfts,
  entriesFound: z.number(),
  entriesLimit: z.number(),
});

export type NftResponse = z.infer<typeof NftResponse>;

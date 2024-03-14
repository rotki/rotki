import { z } from 'zod';
import { NumericString } from '@rotki/common';
import type { AssetInfoWithId } from '@/types/asset';

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
  name: z.string().nullable(),
  largeImage: z.string().nullable(),
});

const Nft = z.object({
  tokenIdentifier: z.string().min(1),
  name: z.string().nullable(),
  collection: NftCollectionInfo,
  backgroundColor: z.string().nullable(),
  imageUrl: z.string().nullable(),
  externalLink: z
    .string()
    .nullable()
    .transform(item => item || undefined),
  permalink: z.string().nullable(),
  priceUsd: NumericString,
  priceInAsset: NumericString,
  priceAsset: z.string(),
});

export type Nft = z.infer<typeof Nft>;

export interface GalleryNft extends Nft {
  address: string;
}

const Nfts = z.record(z.array(Nft));

export type Nfts = z.infer<typeof Nfts>;

export const NftResponse = z.object({
  addresses: Nfts,
  entriesFound: z.number(),
  entriesLimit: z.number(),
});

export type NftResponse = z.infer<typeof NftResponse>;

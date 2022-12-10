import { type BigNumber, NumericString } from '@rotki/common';
import { z } from 'zod';

export enum PrivacyMode {
  NORMAL = 0,
  SEMI_PRIVATE = 1,
  PRIVATE = 2
}

export interface Pinned {
  name: string;
  props: Record<string, any>;
}

export const SyncConflictPayload = z.object({
  localLastModified: z.number(),
  remoteLastModified: z.number()
});

export type SyncConflictPayload = z.infer<typeof SyncConflictPayload>;

export interface SyncConflict {
  readonly message: string;
  readonly payload: SyncConflictPayload | null;
}

export interface PremiumCredentialsPayload {
  readonly username: string;
  readonly apiKey: string;
  readonly apiSecret: string;
}

export interface ChangePasswordPayload {
  readonly currentPassword: string;
  readonly newPassword: string;
}

const NftCollectionInfo = z.object({
  bannerImage: z.string().nullable(),
  description: z.string().nullable(),
  name: z.string().nullable(),
  largeImage: z.string().nullable()
});

const Nft = z.object({
  tokenIdentifier: z.string().nonempty(),
  name: z.string().nullable(),
  collection: NftCollectionInfo,
  backgroundColor: z.string().nullable(),
  imageUrl: z.string().nullable(),
  externalLink: z.string().nullable(),
  permalink: z.string().nullable(),
  priceEth: NumericString,
  priceUsd: NumericString
});

export type Nft = z.infer<typeof Nft>;

export interface GalleryNft extends Omit<Nft, 'priceEth'> {
  address: string;
  priceInAsset: BigNumber;
  priceAsset: string;
}

const Nfts = z.record(z.array(Nft));

export type Nfts = z.infer<typeof Nfts>;

export const NftResponse = z.object({
  addresses: Nfts,
  entriesFound: z.number(),
  entriesLimit: z.number()
});

export type NftResponse = z.infer<typeof NftResponse>;

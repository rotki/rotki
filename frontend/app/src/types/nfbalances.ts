import { z } from 'zod';
import { PriceInformation } from '@/types/prices';
import { CollectionCommonFields } from '@/types/collection';
import type { IgnoredAssetsHandlingType } from '@/types/asset';
import type { PaginationRequestPayload } from '@/types/common';

export const NonFungibleBalance = PriceInformation.merge(
  z.object({
    name: z.string().nullable(),
    id: z.string().min(1),
    imageUrl: z.string().nullable(),
    isLp: z.boolean().nullish(),
    collectionName: z.string().nullable(),
  }),
);

export type NonFungibleBalance = z.infer<typeof NonFungibleBalance>;

const NonFungibleBalanceArray = z.array(NonFungibleBalance);

export const NonFungibleBalancesCollectionResponse = CollectionCommonFields.extend({
  entries: NonFungibleBalanceArray,
});

export type NonFungibleBalancesCollectionResponse = z.infer<typeof NonFungibleBalancesCollectionResponse>;

export interface NonFungibleBalancesRequestPayload extends PaginationRequestPayload<NonFungibleBalance> {
  readonly name?: string;
  readonly collectionName?: string;
  readonly ignoredAssetsHandling?: IgnoredAssetsHandlingType;
}

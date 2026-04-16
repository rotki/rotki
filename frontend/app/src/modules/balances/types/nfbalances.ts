import type { IgnoredAssetsHandlingType } from '@/modules/assets/types';
import type { PaginationRequestPayload } from '@/modules/core/common/common-types';
import { z } from 'zod/v4';
import { PriceInformation } from '@/modules/assets/prices/price-types';
import { CollectionCommonFields } from '@/modules/core/common/collection';

export const NonFungibleBalance = z.object({
  ...PriceInformation.shape,
  collectionName: z.string().nullable(),
  id: z.string().min(1),
  imageUrl: z.string().nullable(),
  isLp: z.boolean().nullish(),
  name: z.string().nullable(),
});

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

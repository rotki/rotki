import { NumericString } from '@rotki/common';
import { z } from 'zod';
import { PriceInformation } from '@/services/assets/types';
import { type IgnoredAssetsHandlingType } from '@/types/assets';
import { type PaginationRequestPayload } from '@/types/common';

export const NonFungibleBalance = PriceInformation.merge(
  z.object({
    name: z.string().nullable(),
    id: z.string().min(1),
    imageUrl: z.string().nullable(),
    isLp: z.boolean().nullish(),
    collectionName: z.string().nullable()
  })
);
export type NonFungibleBalance = z.infer<typeof NonFungibleBalance>;

const NonFungibleBalanceArray = z.array(NonFungibleBalance);
type NonFungibleBalanceArray = z.infer<typeof NonFungibleBalanceArray>;

export const NonFungibleBalances = z.record(NonFungibleBalanceArray);
export type NonFungibleBalances = z.infer<typeof NonFungibleBalances>;

export const NonFungibleBalancesCollectionResponse = z
  .object({
    entries: NonFungibleBalances,
    entriesFound: z.number(),
    entriesLimit: z.number().default(-1),
    entriesTotal: z.number(),
    totalUsdValue: NumericString.nullish()
  })
  .transform(response => {
    const mappedEntries: NonFungibleBalanceArray = Object.values(
      response.entries
    ).flat();

    return {
      ...response,
      entries: mappedEntries
    };
  });

export type NonFungibleBalancesCollectionResponse = z.infer<
  typeof NonFungibleBalancesCollectionResponse
>;

export interface NonFungibleBalancesRequestPayload
  extends PaginationRequestPayload<NonFungibleBalance> {
  readonly name?: string;
  readonly collectionName?: string;
  readonly ignoredAssetsHandling?: IgnoredAssetsHandlingType;
}

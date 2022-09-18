import { z } from 'zod';
import { PriceInformation } from '@/services/assets/types';

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
export const NonFungibleBalances = z.record(NonFungibleBalanceArray);
export type NonFungibleBalances = z.infer<typeof NonFungibleBalances>;

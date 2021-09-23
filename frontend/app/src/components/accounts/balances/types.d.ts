import { NonFungibleBalance } from '@/store/balances/types';

export type PricedNonFungibleBalance = NonFungibleBalance & {
  hasPrice: boolean;
};

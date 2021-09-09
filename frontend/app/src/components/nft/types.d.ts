import { Nft } from '@/store/session/types';

export type NftWithAddress = Nft & { readonly address: string };

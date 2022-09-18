export interface PoapDeliveryDetails {
  readonly amount: string;
  readonly link: string;
  readonly name: string;
  readonly event: string;
}

export interface Airdrop {
  readonly address: string;
  readonly source: AirdropType;
  readonly amount?: string;
  readonly link?: string;
  readonly asset?: string;
  readonly details?: PoapDeliveryDetails[];
}

export interface AirdropDetail {
  readonly amount: string;
  readonly asset: string;
  readonly link: string;
}

export interface PoapDelivery {
  readonly assets: number[];
  readonly event: string;
  readonly link: string;
  readonly name: string;
}

type AirdropDetails = RegularAirdrop & PoapDetails;
type RegularAirdrop = {
  readonly [source in Exclude<AirdropType, 'poap'>]?: AirdropDetail;
};

export interface Airdrops {
  readonly [address: string]: AirdropDetails;
}

export type AirdropType = typeof AIRDROPS[number];
export const AIRDROP_UNISWAP = 'uniswap';
export const AIRDROP_1INCH = '1inch';
export const AIRDROP_TORNADO = 'tornado';
export const AIRDROP_CORNICHON = 'cornichon';
export const AIRDROP_GRAIN = 'grain';
export const AIRDROP_LIDO = 'lido';
export const AIRDROP_FURUCOMBO = 'furucombo';
export const AIRDROP_CURVE = 'curve';
export const AIRDROP_POAP = 'poap';
export const AIRDROP_CONVEX = 'convex';
export const AIRDROP_FOX = 'fox';
export const AIRDROP_ENS = 'ens';
export const AIRDROP_PARASWAP = 'psp';
export const AIRDROP_SADDLE = 'sdl';
export const AIRDROP_COW_GNOSIS = 'cowGnosis';
export const AIRDROP_COW_MAINNET = 'cowMainnet';
export const AIRDROPS = [
  AIRDROP_1INCH,
  AIRDROP_TORNADO,
  AIRDROP_UNISWAP,
  AIRDROP_CORNICHON,
  AIRDROP_COW_GNOSIS,
  AIRDROP_COW_MAINNET,
  AIRDROP_GRAIN,
  AIRDROP_LIDO,
  AIRDROP_FURUCOMBO,
  AIRDROP_CURVE,
  AIRDROP_POAP,
  AIRDROP_CONVEX,
  AIRDROP_FOX,
  AIRDROP_ENS,
  AIRDROP_PARASWAP,
  AIRDROP_SADDLE
] as const;

type PoapDetails = {
  readonly [AIRDROP_POAP]?: PoapDelivery[];
};

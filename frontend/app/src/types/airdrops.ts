import { NumericString } from '@rotki/common';
import { z } from 'zod';

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

export const AIRDROP_SHAPESHIFT = 'shapeshift';

export const AIRDROP_ENS = 'ens';

export const AIRDROP_PARASWAP = 'psp';

export const AIRDROP_SADDLE = 'sdl';

export const AIRDROP_COW_GNOSIS = 'cowGnosis';

export const AIRDROP_COW_MAINNET = 'cowMainnet';

export const AIRDROP_DIVA = 'diva';

const AIRDROPS = [
  AIRDROP_1INCH,
  AIRDROP_TORNADO,
  AIRDROP_UNISWAP,
  AIRDROP_CORNICHON,
  AIRDROP_COW_GNOSIS,
  AIRDROP_COW_MAINNET,
  AIRDROP_DIVA,
  AIRDROP_GRAIN,
  AIRDROP_LIDO,
  AIRDROP_FURUCOMBO,
  AIRDROP_CURVE,
  AIRDROP_POAP,
  AIRDROP_CONVEX,
  AIRDROP_SHAPESHIFT,
  AIRDROP_ENS,
  AIRDROP_PARASWAP,
  AIRDROP_SADDLE
] as const;

const AirdropType = z.enum(AIRDROPS);

export type AirdropType = z.infer<typeof AirdropType>;

const PoapDeliveryDetails = z.object({
  amount: NumericString,
  link: z.string(),
  name: z.string(),
  event: z.string()
});

export type PoapDeliveryDetails = z.infer<typeof PoapDeliveryDetails>;

const Airdrop = z.object({
  address: z.string(),
  source: AirdropType,
  amount: NumericString.optional(),
  link: z.string().optional(),
  asset: z.string().optional(),
  details: z.array(PoapDeliveryDetails).optional()
});

export type Airdrop = z.infer<typeof Airdrop>;

const AirdropDetail = z.object({
  amount: NumericString,
  asset: z.string(),
  link: z.string()
});

export type AirdropDetail = z.infer<typeof AirdropDetail>;

const PoapDelivery = z.object({
  assets: z.array(z.number()),
  event: z.string(),
  link: z.string(),
  name: z.string()
});

export type PoapDelivery = z.infer<typeof PoapDelivery>;

const AirdropDetails = z.record(
  AirdropDetail.or(z.array(PoapDelivery)).optional()
);

export const Airdrops = z.record(AirdropDetails);

export type Airdrops = z.infer<typeof Airdrops>;

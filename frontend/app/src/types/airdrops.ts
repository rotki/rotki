import { NumericString } from '@rotki/common';
import { z } from 'zod';

export const AIRDROP_POAP = 'poap';

const PoapDeliveryDetails = z.object({
  amount: NumericString,
  link: z.string(),
  name: z.string(),
  event: z.string()
});

export type PoapDeliveryDetails = z.infer<typeof PoapDeliveryDetails>;

const Airdrop = z.object({
  address: z.string(),
  source: z.string(),
  amount: NumericString.optional(),
  link: z.string().optional(),
  asset: z.string().optional(),
  claimed: z.boolean().optional(),
  details: z.array(PoapDeliveryDetails).optional()
});

export type Airdrop = z.infer<typeof Airdrop>;

const AirdropDetail = z.object({
  amount: NumericString,
  asset: z.string(),
  claimed: z.boolean(),
  link: z.string()
});

export type AirdropDetail = z.infer<typeof AirdropDetail>;

const PoapDelivery = z.object({
  assets: z.array(z.number()),
  event: z.string(),
  link: z.string(),
  claimed: z.boolean().optional().default(false),
  name: z.string()
});

export type PoapDelivery = z.infer<typeof PoapDelivery>;

const AirdropDetails = z.record(
  AirdropDetail.or(z.array(PoapDelivery)).optional()
);

export const Airdrops = z.record(AirdropDetails);

export type Airdrops = z.infer<typeof Airdrops>;

import { NumericString } from '@rotki/common';
import { z } from 'zod/v4';

export const AIRDROP_POAP = 'poap';

const PoapDeliveryDetails = z.object({
  assets: z.array(z.number()),
  event: z.string(),
  link: z.string(),
  name: z.string(),
});

export type PoapDeliveryDetails = z.infer<typeof PoapDeliveryDetails>;

const Airdrop = z.object({
  address: z.string(),
  amount: NumericString.optional(),
  asset: z.string().optional(),
  claimed: z.boolean().optional(),
  cutoffTime: z.number().optional(),
  details: z.array(PoapDeliveryDetails).optional(),
  hasDecoder: z.boolean().optional(),
  icon: z.string().optional(),
  iconUrl: z.string().optional(),
  link: z.string().optional(),
  source: z.string(),
});

export type Airdrop = z.infer<typeof Airdrop>;

const AirdropDetail = z.object({
  amount: NumericString,
  asset: z.string(),
  claimed: z.boolean(),
  cutoffTime: z.number().optional(),
  hasDecoder: z.boolean().optional(),
  icon: z.string().optional(),
  iconUrl: z.string().optional(),
  link: z.string(),
});

const PoapDelivery = PoapDeliveryDetails.extend({
  claimed: z.boolean().optional().default(false),
  iconUrl: z.string().optional(),
});

export type PoapDelivery = z.infer<typeof PoapDelivery>;

const AirdropDetails = z.record(z.string(), AirdropDetail.or(z.array(PoapDelivery)).optional());

export const Airdrops = z.record(z.string(), AirdropDetails);

export type Airdrops = z.infer<typeof Airdrops>;

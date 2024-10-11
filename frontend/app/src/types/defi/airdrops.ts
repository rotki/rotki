import { NumericString } from '@rotki/common';
import { z } from 'zod';

export const AIRDROP_POAP = 'poap';

const PoapDeliveryDetails = z.object({
  assets: z.array(z.number()),
  link: z.string(),
  name: z.string(),
  event: z.string(),
});

export type PoapDeliveryDetails = z.infer<typeof PoapDeliveryDetails>;

const Airdrop = z.object({
  address: z.string(),
  source: z.string(),
  amount: NumericString.optional(),
  link: z.string().optional(),
  asset: z.string().optional(),
  claimed: z.boolean().optional(),
  details: z.array(PoapDeliveryDetails).optional(),
  cutoffTime: z.number().optional(),
  hasDecoder: z.boolean().optional(),
  icon: z.string().optional(),
  iconUrl: z.string().optional(),
});

export type Airdrop = z.infer<typeof Airdrop>;

const AirdropDetail = z.object({
  amount: NumericString,
  asset: z.string(),
  claimed: z.boolean(),
  cutoffTime: z.number().optional(),
  hasDecoder: z.boolean().optional(),
  link: z.string(),
  icon: z.string().optional(),
  iconUrl: z.string().optional(),
});

const PoapDelivery = PoapDeliveryDetails.extend({
  claimed: z.boolean().optional().default(false),
  iconUrl: z.string().optional(),
});

export type PoapDelivery = z.infer<typeof PoapDelivery>;

const AirdropDetails = z.record(AirdropDetail.or(z.array(PoapDelivery)).optional());

export const Airdrops = z.record(AirdropDetails);

export type Airdrops = z.infer<typeof Airdrops>;

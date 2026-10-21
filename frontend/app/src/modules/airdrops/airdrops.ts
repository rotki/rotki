import { NumericString } from '@rotki/common';
import { z } from 'zod';

const PoapDeliveryDetails = z.object({
  assets: z.array(z.number()),
  event: z.string(),
  link: z.string(),
  name: z.string(),
});

export type PoapDeliveryDetails = z.infer<typeof PoapDeliveryDetails>;

export interface Airdrop {
  address: string;
  amount?: z.infer<typeof NumericString>;
  asset?: string;
  claimed?: boolean;
  cutoffTime?: number;
  details?: PoapDeliveryDetails[];
  hasDecoder?: boolean;
  icon?: string;
  iconUrl?: string;
  link?: string;
  source: string;
}

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

type PoapDelivery = z.infer<typeof PoapDelivery>;

const AirdropDetails = z.record(z.string(), AirdropDetail.or(z.array(PoapDelivery)).optional());

export const Airdrops = z.record(z.string(), AirdropDetails);

export type Airdrops = z.infer<typeof Airdrops>;

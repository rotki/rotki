import { z } from 'zod';

export interface ActionResult<T> {
  readonly result: T;
  readonly message: string;
}

export const BaseAsset = z.object({
  identifier: z.string(),
  coingecko: z.string().nullish(),
  cryptocompare: z.string().nullish(),
  started: z.number().nullish(),
  name: z.string().nullish(),
  symbol: z.string().nullish(),
  swappedFor: z.string().nullish(),
});

export type BaseAsset = z.infer<typeof BaseAsset>;

export const SupportedAsset = BaseAsset.extend({
  active: z.boolean().optional(),
  ended: z.number().nullish(),
  decimals: z.number().nullish(),
  assetType: z.string(),
  forked: z.string().nullish(),
  ethereumAddress: z.string().nullish(),
})

export type SupportedAsset = z.infer<typeof SupportedAsset>;

import type { ActionDataEntry } from '@/types/action';
import { z } from 'zod/v4';

export type AllLocation = Record<
  string,
  Omit<ActionDataEntry, 'identifier'> & {
    isExchange?: boolean;
    exchangeDetails?: {
      isExchangeWithPassphrase?: boolean;
      isExchangeWithKey?: boolean;
      isExchangeWithoutApiSecret?: boolean;
      experimental?: boolean;
    };
  }
>;

const ExchangeDetailsSchema = z.object({
  isExchangeWithPassphrase: z.boolean().optional(),
  isExchangeWithKey: z.boolean().optional(),
  isExchangeWithoutApiSecret: z.boolean().optional(),
  experimental: z.boolean().optional(),
});

const AllLocationEntrySchema = z.object({
  label: z.string().optional(),
  icon: z.string().optional(),
  image: z.string().optional(),
  darkmodeImage: z.string().optional(),
  color: z.string().optional(),
  detailPath: z.string().optional(),
  isExchange: z.boolean().optional(),
  exchangeDetails: ExchangeDetailsSchema.optional(),
});

export const AllLocationSchema = z.record(z.string(), AllLocationEntrySchema);

export const AllLocationResponseSchema = z.object({
  locations: AllLocationSchema,
});

export type AllLocationResponse = z.infer<typeof AllLocationResponseSchema>;

export const LocationLabelSchema = z.object({
  location: z.string(),
  locationLabel: z.string(),
});

export type LocationLabel = z.infer<typeof LocationLabelSchema>;

export const LocationLabelsSchema = z.array(LocationLabelSchema);

/** @deprecated Use LocationLabelSchema instead */
export const LocationLabel = LocationLabelSchema;

/** @deprecated Use LocationLabelsSchema instead */
export const LocationLabels = LocationLabelsSchema;

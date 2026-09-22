import type { RuiIcons } from '@rotki/ui-library';
import type { ActionDataEntry } from '@/modules/core/common/action';
import { z } from 'zod';

export interface TradeLocationData {
  readonly identifier: string;
  readonly name: string;
  readonly icon?: RuiIcons | null;
  readonly image?: string | null;
  readonly detailPath?: string | null;
}

export type AllLocation = Record<
  string,
  Omit<ActionDataEntry, 'identifier'> & {
    isExchange?: boolean;
  }
>;

const AllLocationEntrySchema = z.object({
  label: z.string().optional(),
  icon: z.string().optional(),
  image: z.string().optional(),
  darkmodeImage: z.string().optional(),
  color: z.string().optional(),
  detailPath: z.string().optional(),
  isExchange: z.boolean().optional(),
});

const AllLocationSchema = z.record(z.string(), AllLocationEntrySchema);

export const AllLocationResponseSchema = z.object({
  locations: AllLocationSchema,
});

export type AllLocationResponse = z.infer<typeof AllLocationResponseSchema>;

/**
 * Locations the user's data is directly assigned to, and the further ancestors needed to show
 * their paths in the location tree.
 */
export const AssociatedLocationsSchema = z.object({
  locations: z.array(z.string()),
  ancestors: z.array(z.string()),
});

export type AssociatedLocations = z.infer<typeof AssociatedLocationsSchema>;

const LocationLabelSchema = z.object({
  location: z.string(),
  locationLabel: z.string(),
});

export type LocationLabel = z.infer<typeof LocationLabelSchema>;

export const LocationLabelsSchema = z.array(LocationLabelSchema);

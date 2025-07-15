import { z } from 'zod/v4';
import { EvmChainLikeAddress } from '@/types/history/events';

export const PremiumStatusUpdateData = z.object({
  expired: z.boolean(),
  isPremiumActive: z.boolean(),
});

export type PremiumStatusUpdateData = z.infer<typeof PremiumStatusUpdateData>;

export const DbUpgradeStatusData = z.object({
  currentUpgrade: z.object({
    currentStep: z.number().nonnegative(),
    description: z.string().nullable(),
    totalSteps: z.number().nonnegative(),
    toVersion: z.number().nonnegative(),
  }),
  startVersion: z.number().nonnegative(),
  targetVersion: z.number().nonnegative(),
});

export type DbUpgradeStatusData = z.infer<typeof DbUpgradeStatusData>;

export const DbUploadResult = z.object({
  actionable: z.boolean(),
  message: z.string().nullable(),
  uploaded: z.boolean(),
});

export type DbUploadResult = z.infer<typeof DbUploadResult>;

export const DataMigrationStatusData = z.object({
  currentMigration: z.object({
    currentStep: z.number().nonnegative(),
    description: z.string().nullable(),
    totalSteps: z.number().nonnegative(),
    version: z.number().nonnegative(),
  }),
  startVersion: z.number().nonnegative(),
  targetVersion: z.number().nonnegative(),
});

export type DataMigrationStatusData = z.infer<typeof DataMigrationStatusData>;

export const MigratedAddresses = z.array(EvmChainLikeAddress);

export type MigratedAddresses = z.infer<typeof MigratedAddresses>;

import { z } from 'zod/v4';

export const PremiumStatusUpdateData = z.object({
  expired: z.boolean(),
  isPremiumActive: z.boolean(),
});

export type PremiumStatusUpdateData = z.infer<typeof PremiumStatusUpdateData>;

export const DbUploadResult = z.object({
  actionable: z.boolean(),
  message: z.string().nullable(),
  uploaded: z.boolean(),
});

export type DbUploadResult = z.infer<typeof DbUploadResult>;

export const DatabaseUploadProgress = z.discriminatedUnion('type', [
  z.object({
    type: z.literal('compressing'),
  }),
  z.object({
    type: z.literal('encrypting'),
  }),
  z.object({
    currentChunk: z.number().nonnegative(),
    totalChunks: z.number().nonnegative(),
    type: z.literal('uploading'),
  }),
]);

export type DatabaseUploadProgress = z.infer<typeof DatabaseUploadProgress>;

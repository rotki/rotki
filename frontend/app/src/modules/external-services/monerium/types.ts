import { z } from 'zod/v4';

const MoneriumProfileSchema = z.object({
  id: z.string(),
  kind: z.string().optional(),
  name: z.string().optional(),
});

export type MoneriumProfile = z.infer<typeof MoneriumProfileSchema>;

export const MoneriumStatusSchema = z.object({
  authenticated: z.boolean(),
  defaultProfileId: z.string().optional(),
  expiresAt: z.number().optional(),
  profiles: z.array(MoneriumProfileSchema).optional(),
  tokenType: z.string().optional(),
  userEmail: z.string().optional(),
});

export type MoneriumStatus = z.infer<typeof MoneriumStatusSchema>;

export const MoneriumAuthResultSchema = z.object({
  defaultProfileId: z.string().optional(),
  message: z.string(),
  profiles: z.array(MoneriumProfileSchema).optional(),
  success: z.boolean(),
  userEmail: z.string().optional(),
});

export type MoneriumAuthResult = z.infer<typeof MoneriumAuthResultSchema>;

export type MoneriumOAuthResult = Omit<MoneriumAuthResult, 'success'>;

export const MoneriumDisconnectResultSchema = z.object({
  success: z.boolean(),
});

export type MoneriumDisconnectResult = z.infer<typeof MoneriumDisconnectResultSchema>;

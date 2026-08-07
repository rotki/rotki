import { z } from 'zod';

export const McpPrivacyMode = {
  BALANCED: 'balanced',
  RAW: 'raw',
  STRICT: 'strict',
} as const;

export const McpPrivacyModeEnum = z.enum(McpPrivacyMode);

export type McpPrivacyMode = z.infer<typeof McpPrivacyModeEnum>;

export const McpTokenSchema = z.object({
  accessToken: z.string().min(1),
  expiresAt: z.number(),
  tokenType: z.literal('Bearer'),
});

export type McpToken = z.infer<typeof McpTokenSchema>;

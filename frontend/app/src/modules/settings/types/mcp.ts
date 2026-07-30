import { z } from 'zod';

export const McpTokenSchema = z.object({
  accessToken: z.string().min(1),
  expiresAt: z.number(),
  tokenType: z.literal('Bearer'),
});

export type McpToken = z.infer<typeof McpTokenSchema>;

import { z } from 'zod/v4';

/**
 * WebSocket message schemas for wallet bridge communication
 */

// Notification schema
export const WalletBridgeNotificationSchema = z.object({
  type: z.enum(['close_tab', 'reconnected', 'wallet_event']),
  eventName: z.string().optional(),
  eventData: z.unknown().optional(),
});

export type WalletBridgeNotification = z.infer<typeof WalletBridgeNotificationSchema>;

// Request schema
export const WalletBridgeRequestSchema = z.object({
  id: z.string(),
  jsonrpc: z.literal('2.0'),
  method: z.string(),
  params: z.unknown().optional(),
});

export type WalletBridgeRequest = z.infer<typeof WalletBridgeRequestSchema>;

// Response schema
export const WalletBridgeResponseSchema = z.object({
  id: z.string(),
  jsonrpc: z.literal('2.0'),
  result: z.unknown().optional(),
  error: z.object({
    code: z.number(),
    message: z.string(),
  }).optional(),
});

export type WalletBridgeResponse = z.infer<typeof WalletBridgeResponseSchema>;

// Union of all message types
export const WalletBridgeMessageSchema = z.union([
  WalletBridgeNotificationSchema,
  WalletBridgeRequestSchema,
  WalletBridgeResponseSchema,
]);

export type WalletBridgeMessage = z.infer<typeof WalletBridgeMessageSchema>;

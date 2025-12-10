import { z } from 'zod/v4';

/**
 * Unified Wallet Bridge Types with Runtime Validation
 * Shared between frontend and Electron main process
 */

// JSON-RPC 2.0 Base Schema
const JsonRpcBaseSchema = z.object({
  id: z.union([z.string(), z.number()]),
  jsonrpc: z.literal('2.0'),
});

// Wallet Bridge Request Schema (JSON-RPC format)
const WalletBridgeRequestSchema = JsonRpcBaseSchema.extend({
  method: z.string().min(1),
  params: z.array(z.unknown()).optional(),
});

export type WalletBridgeRequest = z.infer<typeof WalletBridgeRequestSchema>;

// RPC Error Schema
const RpcErrorSchema = z.object({
  code: z.number(),
  message: z.string(),
  data: z.unknown().optional(),
});

// Wallet Bridge Response Schema
export const WalletBridgeResponseSchema = JsonRpcBaseSchema.extend({
  result: z.unknown().optional(),
  error: RpcErrorSchema.optional(),
}).refine(
  data => (data.result !== undefined) !== (data.error !== undefined),
  { message: 'Response must have either result or error, but not both' },
);

export type WalletBridgeResponse = z.infer<typeof WalletBridgeResponseSchema>;

// Notification Types
const NotificationTypeSchema = z.enum([
  'close_tab',
  'reconnected',
  'wallet_event',
]);

// Wallet Bridge Notification Schema
const WalletBridgeNotificationSchema = z.object({
  type: NotificationTypeSchema,
  eventName: z.string().optional(),
  eventData: z.unknown().optional(),
  data: z.unknown().optional(),
});

export type WalletBridgeNotification = z.infer<typeof WalletBridgeNotificationSchema>;

// Union of all possible WebSocket messages
export const WalletBridgeMessageSchema = z.union([
  WalletBridgeRequestSchema,
  WalletBridgeResponseSchema,
  WalletBridgeNotificationSchema,
]);

type WalletBridgeMessage = z.infer<typeof WalletBridgeMessageSchema>;

// Type guards
export function isWalletBridgeRequest(message: unknown): message is WalletBridgeRequest {
  return WalletBridgeRequestSchema.safeParse(message).success;
}

export function isWalletBridgeNotification(message: unknown): message is WalletBridgeNotification {
  return WalletBridgeNotificationSchema.safeParse(message).success;
}

// Validation functions
export function validateWalletBridgeMessage(message: unknown): WalletBridgeMessage {
  const result = WalletBridgeMessageSchema.safeParse(message);
  if (!result.success) {
    throw new Error(`Invalid wallet bridge message: ${result.error.message}`);
  }
  return result.data;
}

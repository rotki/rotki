import { z } from 'zod/v4';

/**
 * Wallet Bridge Types with Runtime Validation
 */

// JSON-RPC 2.0 Base Schema
const JsonRpcBaseSchema = z.object({
  id: z.union([z.string(), z.number()]),
  jsonrpc: z.literal('2.0'),
});

// RPC Request Schema
export const RpcRequestSchema = z.object({
  method: z.string().min(1),
  params: z.array(z.unknown()).optional(),
});

export type RpcRequest = z.infer<typeof RpcRequestSchema>;

// Wallet Bridge Request Schema (JSON-RPC format)
export const WalletBridgeRequestSchema = JsonRpcBaseSchema.extend({
  method: z.string().min(1),
  params: z.array(z.unknown()).optional(),
});

export type WalletBridgeRequest = z.infer<typeof WalletBridgeRequestSchema>;

// RPC Error Schema
export const RpcErrorSchema = z.object({
  code: z.number(),
  data: z.unknown().optional(),
  message: z.string(),
});

export type RpcError = z.infer<typeof RpcErrorSchema>;

// Wallet Bridge Response Schema
export const WalletBridgeResponseSchema = JsonRpcBaseSchema.extend({
  error: RpcErrorSchema.optional(),
  result: z.unknown().optional(),
}).refine(
  data => (data.result !== undefined) !== (data.error !== undefined),
  { message: 'Response must have either result or error, but not both' },
);

export type WalletBridgeResponse = z.infer<typeof WalletBridgeResponseSchema>;

// Notification Types
export const NotificationTypeSchema = z.enum(['close_tab', 'reconnected']);

export const WalletBridgeNotificationSchema = z.object({
  data: z.unknown().optional(),
  type: NotificationTypeSchema,
});

export type WalletBridgeNotification = z.infer<typeof WalletBridgeNotificationSchema>;

export type NotificationType = z.infer<typeof NotificationTypeSchema>;

// Union of all possible WebSocket messages
export const WalletBridgeMessageSchema = z.union([
  WalletBridgeRequestSchema,
  WalletBridgeResponseSchema,
  WalletBridgeNotificationSchema,
]);

export type WalletBridgeMessage = z.infer<typeof WalletBridgeMessageSchema>;

// Connection Status
export const ConnectionStatusSchema = z.enum(['connected', 'disconnected', 'reconnected']);

export type ConnectionStatus = z.infer<typeof ConnectionStatusSchema>;

// Wallet Bridge Events
export interface WalletBridgeEvents {
  request: [WalletBridgeRequest];
  response: [WalletBridgeResponse];
  notification: [WalletBridgeNotification];
  connection: [ConnectionStatus];
  error: [Error];
}

export type WalletBridgeEventName = keyof WalletBridgeEvents;

// Type guards
export function isWalletBridgeRequest(message: unknown): message is WalletBridgeRequest {
  return WalletBridgeRequestSchema.safeParse(message).success;
}

export function isWalletBridgeResponse(message: unknown): message is WalletBridgeResponse {
  return WalletBridgeResponseSchema.safeParse(message).success;
}

export function isWalletBridgeNotification(message: unknown): message is WalletBridgeNotification {
  return WalletBridgeNotificationSchema.safeParse(message).success;
}

export function isValidWalletBridgeMessage(message: unknown): message is WalletBridgeMessage {
  return WalletBridgeMessageSchema.safeParse(message).success;
}

// Validation functions
export function validateWalletBridgeMessage(message: unknown): WalletBridgeMessage {
  const result = WalletBridgeMessageSchema.safeParse(message);
  if (!result.success) {
    throw new Error(`Invalid wallet bridge message: ${result.error.message}`);
  }
  return result.data;
}

export function validateRpcRequest(request: unknown): RpcRequest {
  const result = RpcRequestSchema.safeParse(request);
  if (!result.success) {
    throw new Error(`Invalid RPC request: ${result.error.message}`);
  }
  return result.data;
}

// Common Ethereum RPC method types for better type safety
export interface EthereumRpcMethods {
  eth_accounts: {
    params: [];
    result: string[];
  };
  eth_chainId: {
    params: [];
    result: string;
  };
  eth_requestAccounts: {
    params: [];
    result: string[];
  };
  eth_getBalance: {
    params: [string, string?];
    result: string;
  };
  eth_sendTransaction: {
    params: [{ from: string; to?: string; value?: string; data?: string; gas?: string; gasPrice?: string }];
    result: string;
  };
  eth_getBlockByNumber: {
    params: [string, boolean];
    result: {
      number: string;
      hash: string;
      parentHash: string;
      timestamp: string;
      [key: string]: unknown;
    } | null;
  };
}

export type EthereumMethodName = keyof EthereumRpcMethods;

// Type-safe RPC request builder
export function createRpcRequest<T extends EthereumMethodName>(
  method: T,
  params: EthereumRpcMethods[T]['params'],
): RpcRequest {
  return {
    method,
    params: params as unknown[],
  };
}

import { pipe, type ResultType as Result } from 'plainfp';
import { err, flatMap, fromThrowable, ok } from 'plainfp/result';
import * as z from 'zod/mini';

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
const WalletBridgeRequestSchema = z.extend(JsonRpcBaseSchema, {
  method: z.string().check(z.minLength(1)),
  params: z.optional(z.array(z.unknown())),
});

export type WalletBridgeRequest = z.infer<typeof WalletBridgeRequestSchema>;

// RPC Error Schema
const RpcErrorSchema = z.object({
  code: z.number(),
  message: z.string(),
  data: z.optional(z.unknown()),
});

// Wallet Bridge Response Schema
export const WalletBridgeResponseSchema = z.extend(JsonRpcBaseSchema, {
  result: z.optional(z.unknown()),
  error: z.optional(RpcErrorSchema),
}).check(z.refine(
  data => (data.result !== undefined) !== (data.error !== undefined),
  { message: 'Response must have either result or error, but not both' },
));

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
  eventName: z.optional(z.string()),
  eventData: z.optional(z.unknown()),
  data: z.optional(z.unknown()),
});

export type WalletBridgeNotification = z.infer<typeof WalletBridgeNotificationSchema>;

// Union of all possible WebSocket messages
const WalletBridgeMessageSchema = z.union([
  WalletBridgeRequestSchema,
  WalletBridgeResponseSchema,
  WalletBridgeNotificationSchema,
]);

export type WalletBridgeMessage = z.infer<typeof WalletBridgeMessageSchema>;

export function isWalletBridgeRequest(message: unknown): message is WalletBridgeRequest {
  return WalletBridgeRequestSchema.safeParse(message).success;
}

export function isWalletBridgeNotification(message: unknown): message is WalletBridgeNotification {
  return WalletBridgeNotificationSchema.safeParse(message).success;
}

export type WalletBridgeParseError =
  | { cause: unknown; kind: 'invalid-json' }
  | { cause: unknown; kind: 'invalid-message'; raw: unknown };

/**
 * Parses one frame off the bridge socket, naming which of the two steps rejected it.
 *
 * @remarks
 * `invalid-message` keeps the decoded value, so a caller can still answer a request whose `id` is
 * readable even though the rest of it is not.
 */
export function parseWalletBridgeMessage(text: string): Result<WalletBridgeMessage, WalletBridgeParseError> {
  return pipe(
    fromThrowable((): unknown => JSON.parse(text), (cause): WalletBridgeParseError => ({ cause, kind: 'invalid-json' })),
    flatMap((raw) => {
      const parsed = WalletBridgeMessageSchema.safeParse(raw);
      return parsed.success
        ? ok(parsed.data)
        : err<WalletBridgeParseError>({ cause: parsed.error, kind: 'invalid-message', raw });
    }),
  );
}

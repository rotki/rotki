import { z } from 'zod';

export const MESSAGE_WARNING = 'warning';
const MESSAGE_ERROR = 'error';

const MessageVerbosity = z.enum([MESSAGE_WARNING, MESSAGE_ERROR]);

export const LegacyMessageData = z.object({
  verbosity: MessageVerbosity,
  value: z.string()
});

export type LegacyMessageData = z.infer<typeof LegacyMessageData>;

export const BalanceSnapshotError = z.object({
  location: z.string(),
  error: z.string()
});

export type BalanceSnapshotError = z.infer<typeof BalanceSnapshotError>;

export enum SocketMessageType {
  LEGACY = 'legacy',
  BALANCES_SNAPSHOT_ERROR = 'balance_snapshot_error'
}

type MessageData = {
  [SocketMessageType.LEGACY]: LegacyMessageData;
  [SocketMessageType.BALANCES_SNAPSHOT_ERROR]: BalanceSnapshotError;
};

export interface WebsocketMessage<T extends SocketMessageType> {
  readonly type: T;
  readonly data: MessageData[T];
}

import type { RuiIcons } from '@rotki/ui-library';
import type { BankConnection } from '@/modules/banks/types';
import { type MessageKey, msg } from '@/message-key';

export type BankConnectionState = 'authentication' | 'expired' | 'failed' | 'ok';

export interface BankConnectionStatusDisplay {
  readonly icon: RuiIcons;
  readonly textClass: string;
  /** The full status, which names the error for a failure. */
  readonly text: MessageKey;
  /** The status in a couple of words, for a place too narrow for the error. */
  readonly short: MessageKey;
  readonly action: MessageKey;
}

/**
 * How each state shows, in the colour and icon every bank surface uses for it: a pending TAN cannot
 * wait, an expired one can.
 */
const BANK_CONNECTION_STATUSES: Readonly<Record<Exclude<BankConnectionState, 'ok'>, BankConnectionStatusDisplay>> = {
  authentication: {
    action: msg.$t('bank_balances.status.authenticate'),
    icon: 'lu-shield-alert',
    short: msg.$t('bank_balances.status.short.authentication'),
    text: msg.$t('bank_balances.status.authentication'),
    textClass: 'text-rui-error',
  },
  expired: {
    action: msg.$t('bank_settings.authentication.sync_again'),
    icon: 'lu-shield-x',
    short: msg.$t('bank_balances.status.short.expired'),
    text: msg.$t('bank_balances.status.expired'),
    textClass: 'text-rui-warning',
  },
  failed: {
    action: msg.$t('bank_balances.status.review'),
    icon: 'lu-circle-alert',
    short: msg.$t('bank_balances.status.short.failed'),
    text: msg.$t('bank_balances.status.failed'),
    textClass: 'text-rui-error',
  },
};

/** A pending TAN outranks an older failure: answering it is what unblocks the connection. */
export function bankConnectionState({ syncStatus }: Pick<BankConnection, 'syncStatus'>): BankConnectionState {
  if (syncStatus.authChallenge)
    return 'authentication';
  if (syncStatus.authExpired)
    return 'expired';
  if (syncStatus.lastError)
    return 'failed';
  return 'ok';
}

/** How a connection's state shows, or nothing for a connection that is fine. */
export function bankConnectionStatus(connection: Pick<BankConnection, 'syncStatus'>): BankConnectionStatusDisplay | undefined {
  const state = bankConnectionState(connection);
  return state === 'ok' ? undefined : BANK_CONNECTION_STATUSES[state];
}

import type { ComputedRef } from 'vue';
import type { BankConnection } from '@/modules/banks/types';
import { startPromise } from '@shared/utils';
import { none, type Option, some } from 'plainfp/option';
import { useBankConnectionsStore } from '@/modules/banks/use-bank-connections-store';
import { useBankName } from '@/modules/banks/use-bank-name';
import { useBanks } from '@/modules/banks/use-banks';
import { type ActionItem, type ActionTarget, ActionUrgency, applicable, createActionItem } from '@/modules/core/action-center/types';

/**
 * A row id for a connection, kebab-case since it ends up in a `data-testid`.
 *
 * @remarks
 * The connection identifier never changes, also across a rename, so seen and snooze state kept by
 * this id stay with the connection.
 */
function connectionRowId(prefix: string, { identifier }: BankConnection): string {
  return `${prefix}-${identifier}`;
}

/**
 * The bank rows: one per connection waiting on an authentication, and one per connection whose last
 * authentication the bank rejected or let expire.
 *
 * @remarks
 * Read from the connections every `GET /banks` refreshes, so a challenge raised by a sync, a balance
 * query or a setup lands here without a notification of its own. A pending challenge is `BLOCKING`,
 * since the bank lets it expire; an expired one is a decision, since syncing again raises a fresh
 * challenge whenever the user is ready.
 */
export function useBankRows(): ComputedRef<ActionItem[]> {
  const { t } = useI18n({ useScope: 'global' });
  const store = useBankConnectionsStore();
  const { connections } = storeToRefs(store);
  const { startOverAuthentication, syncBanks } = useBanks();
  const { bankNameOf } = useBankName();

  function params(connection: BankConnection): Record<string, string> {
    return { location: bankNameOf(connection), name: connection.name };
  }

  /**
   * The row of a connection waiting on a TAN.
   *
   * @remarks
   * It stays until the TAN is answered, since only the bank knows when one lapsed. Starting over
   * drops it and syncs again, which is the way out of a TAN the user will not answer.
   */
  function authenticationRow(connection: BankConnection): ActionItem {
    const { identifier } = connection;
    return createActionItem<ActionTarget, string>({
      actionLabel: t('action_center.rows.integrations.bank_authentication.action'),
      count: 1,
      description: t('action_center.rows.integrations.bank_authentication.description', params(connection)),
      icon: 'lu-shield-alert',
      id: connectionRowId('bank-authentication', connection),
      options: [{
        icon: 'lu-rotate-ccw',
        id: 'start-over',
        label: t('action_center.rows.integrations.bank_authentication.start_over'),
        target: { kind: 'run', run: () => startPromise(startOverAuthentication(connection)) },
      }],
      target: { kind: 'route', to: { name: '/api-keys/banks/', query: { authenticate: identifier } } },
      title: t('action_center.rows.integrations.bank_authentication.title'),
      urgency: ActionUrgency.BLOCKING,
    });
  }

  /**
   * The row of a connection whose last TAN expired.
   *
   * @remarks
   * Not snoozable: every expiry of a connection has the same id and a count of 1, so a snooze could
   * not tell the next one from this one and would hide it.
   */
  function expiredRow(connection: BankConnection): ActionItem {
    const { identifier } = connection;
    return createActionItem<ActionTarget, string>({
      actionLabel: t('action_center.rows.integrations.bank_authentication_expired.action'),
      count: 1,
      description: t('action_center.rows.integrations.bank_authentication_expired.description', params(connection)),
      icon: 'lu-shield-x',
      id: connectionRowId('bank-authentication-expired', connection),
      snoozable: false,
      target: { kind: 'run', run: () => startPromise(syncBanks({ identifier })) },
      title: t('action_center.rows.integrations.bank_authentication_expired.title'),
      urgency: ActionUrgency.DECISION,
    });
  }

  /**
   * The row a connection raises, if any.
   *
   * @remarks
   * An app approval asks nothing to be typed, but it expires all the same, so it is blocking too.
   */
  function rowFor(connection: BankConnection): Option<ActionItem> {
    const { authChallenge, authExpired } = connection.syncStatus;
    if (authChallenge)
      return some(authenticationRow(connection));
    return authExpired ? some(expiredRow(connection)) : none;
  }

  return computed<ActionItem[]>(() => applicable(get(connections).map(rowFor)));
}

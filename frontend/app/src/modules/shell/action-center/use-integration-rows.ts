import type { ExternalServiceName } from '@/modules/integrations/types';
import { toHumanReadable } from '@rotki/common';
import { get } from '@vueuse/shared';
import { storeToRefs } from 'pinia';
import { none, type Option, some } from 'plainfp/option';
import { computed, type ComputedRef, watch } from 'vue';
import { useI18n } from 'vue-i18n';
import { useConnectedExchangesStore } from '@/modules/balances/exchanges/use-connected-exchanges-store';
import { useExchangeKeyConditions } from '@/modules/balances/exchanges/use-exchange-key-conditions';
import { type ActionItem, type ActionTarget, ActionUrgency, applicable, createActionItem } from '@/modules/core/action-center/types';
import { useMoneriumOAuth } from '@/modules/integrations/monerium/use-monerium-auth';
import { ORACLE_SETTINGS } from '@/modules/shell/action-center/row-options';
import { useBankRows } from '@/modules/shell/action-center/use-bank-rows';
import { serviceSettings, useMissingKeyRows } from '@/modules/shell/action-center/use-missing-key-rows';
import { conditionRowId, type RaisedCondition, RaisedConditionKind, type RaisedConditionOf, SessionCause, useRaisedConditionsStore } from '@/modules/shell/action-center/use-raised-conditions-store';

type SessionCondition = RaisedConditionOf<typeof RaisedConditionKind.MONERIUM_SESSION | typeof RaisedConditionKind.GNOSIS_PAY_SESSION>;

/**
 * The integration rows: bank connections waiting on a TAN (see {@link useBankRows}), services a
 * query needed a key for, exchange accounts whose key was refused, price oracles set aside for a
 * while, and sessions that expired.
 *
 * @remarks
 * A missing key leaves as soon as a key is saved for the service or the service is suppressed, and a
 * Monerium session as soon as the status reads authenticated. A Gnosis Pay session has no status to
 * read, so its row stays until a verified sign-in clears the condition. A refused exchange key
 * leaves once the account is saved, renamed or removed, and a set-aside oracle once its penalty
 * ends. The oracle's row asks nothing of the user, since rotki uses it again by itself.
 */
export function useIntegrationRows(): ComputedRef<ActionItem[]> {
  const { t } = useI18n({ useScope: 'global' });

  const { conditions } = storeToRefs(useRaisedConditionsStore());
  const { missingKeyRowFor } = useMissingKeyRows();
  const { authenticated: moneriumAuthenticated } = useMoneriumOAuth();
  const { connectedExchanges } = storeToRefs(useConnectedExchangesStore());
  const { settleDisconnected } = useExchangeKeyConditions();
  const bankRows = useBankRows();

  function exchangeKeyRow(condition: RaisedConditionOf<typeof RaisedConditionKind.EXCHANGE_KEY_REJECTED>): ActionItem {
    const { location, name } = condition;
    const params = { exchange: toHumanReadable(location, 'capitalize'), name };
    return createActionItem<ActionTarget, string>({
      actionLabel: t('action_center.rows.integrations.exchange_key_rejected.action'),
      count: 1,
      description: t('action_center.rows.integrations.exchange_key_rejected.description', params),
      icon: 'lu-key-round',
      id: conditionRowId(condition),
      urgency: ActionUrgency.DECISION,
      target: { kind: 'route', to: { name: '/accounts/exchanges/', query: { location, name } } },
      title: t('action_center.rows.integrations.exchange_key_rejected.title', params),
    });
  }

  function oracleRow(condition: RaisedConditionOf<typeof RaisedConditionKind.ORACLE_PENALIZED>): ActionItem {
    const params = { oracle: toHumanReadable(condition.oracle, 'capitalize') };
    return createActionItem<ActionTarget, string>({
      actionLabel: t('action_center.rows.integrations.oracle_penalized.action'),
      count: 1,
      description: condition.reason === 'timeout'
        ? t('action_center.rows.integrations.oracle_penalized.description_timeout', params)
        : t('action_center.rows.integrations.oracle_penalized.description_errors', params),
      icon: 'lu-chart-line',
      id: conditionRowId(condition),
      urgency: ActionUrgency.AUTOMATIC,
      target: ORACLE_SETTINGS,
      title: t('action_center.rows.integrations.oracle_penalized.title', params),
    });
  }

  function sessionRow(condition: SessionCondition, service: ExternalServiceName, copy: { title: string; description: string }): ActionItem {
    return createActionItem<ActionTarget, string>({
      ...copy,
      actionLabel: condition.cause === SessionCause.NOT_CONNECTED
        ? t('external_services.actions.authenticate')
        : t('external_services.actions.reauthenticate'),
      count: 1,
      icon: 'lu-log-in',
      id: conditionRowId(condition),
      urgency: ActionUrgency.DECISION,
      target: { kind: 'route', to: serviceSettings(service) },
    });
  }

  function gnosisPaySessionCopy(cause: SessionCause): { title: string; description: string } {
    return cause === SessionCause.NOT_CONNECTED
      ? {
          description: t('action_center.rows.integrations.gnosis_pay_session.description_not_connected'),
          title: t('action_center.rows.integrations.gnosis_pay_session.title_not_connected'),
        }
      : {
          description: t('action_center.rows.integrations.gnosis_pay_session.description'),
          title: t('action_center.rows.integrations.gnosis_pay_session.title'),
        };
  }

  function moneriumSessionCopy(cause: SessionCause): { title: string; description: string } {
    return cause === SessionCause.NOT_CONNECTED
      ? {
          description: t('action_center.rows.integrations.monerium_session.description_not_connected'),
          title: t('action_center.rows.integrations.monerium_session.title_not_connected'),
        }
      : {
          description: t('action_center.rows.integrations.monerium_session.description'),
          title: t('action_center.rows.integrations.monerium_session.title'),
        };
  }

  /** The row of a missing or expired session, or none once Monerium reads authenticated again. */
  function sessionRowFor(condition: SessionCondition): Option<ActionItem> {
    if (condition.kind === RaisedConditionKind.GNOSIS_PAY_SESSION)
      return some(sessionRow(condition, 'gnosis_pay', gnosisPaySessionCopy(condition.cause)));

    return get(moneriumAuthenticated)
      ? none
      : some(sessionRow(condition, 'monerium', moneriumSessionCopy(condition.cause)));
  }

  /** The row a condition raises right now, or none when it is resolved or belongs to another module. */
  function rowFor(condition: RaisedCondition): Option<ActionItem> {
    switch (condition.kind) {
      case RaisedConditionKind.MISSING_API_KEY:
        return missingKeyRowFor(condition);
      case RaisedConditionKind.EXCHANGE_KEY_REJECTED:
        return some(exchangeKeyRow(condition));
      case RaisedConditionKind.ORACLE_PENALIZED:
        return some(oracleRow(condition));
      case RaisedConditionKind.MONERIUM_SESSION:
      case RaisedConditionKind.GNOSIS_PAY_SESSION:
        return sessionRowFor(condition);
      case RaisedConditionKind.NO_AVAILABLE_INDEXERS:
      case RaisedConditionKind.PREMIUM_INACTIVE:
      case RaisedConditionKind.BINANCE_PAIRS_MISSING:
        return none;
    }
  }

  watch(connectedExchanges, settleDisconnected);

  return computed<ActionItem[]>(() => [...get(bankRows), ...applicable(get(conditions).map(rowFor))]);
}

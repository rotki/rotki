import type { Exchange } from '@/modules/balances/types/exchanges';
import { err, isErr, map as mapResult, type Result } from 'plainfp/result';
import { msg } from '@/message-key';
import { ApiKeyMissingError } from '@/modules/core/api/types/errors';
import { logger } from '@/modules/core/common/logging/logging';
import { useNotifications } from '@/modules/core/notifications/use-notifications';
import { isActionable, Skipped, type TaskError } from '@/modules/core/tasks/task-result';
import { useHistoryEventsApi } from '@/modules/history/api/events/use-history-events-api';
import { OnlineHistoryEventsQueryType } from '@/modules/history/events/schemas';
import { onlineEventsActivityId } from '@/modules/history/events/tx/sync-activity';
import { useExchangeEventsRefresh } from '@/modules/history/events/tx/use-exchange-events-refresh';
import { useMoneriumOAuth } from '@/modules/integrations/monerium/use-monerium-auth';
import { PremiumFeature, useFeatureAccess } from '@/modules/premium/use-feature-access';
import { Module, useModuleEnabled } from '@/modules/session/use-module-enabled';
import { useExternalApiKeys } from '@/modules/settings/api-keys/external/use-external-api-keys';
import { SyncWarningSource, useSyncWarningsStore } from '@/modules/shell/sync-progress/use-sync-warnings-store';
import { activityLabelFor } from '@/modules/task-center/activity-labels';
import { type ActivityId, ActivityKind } from '@/modules/task-center/core/types';
import { useNativeTask } from '@/modules/task-center/use-native-task';

interface UseRefreshHandlersReturn {
  queryAllExchangeEvents: (exchanges: Exchange[], parent?: ActivityId) => Promise<Result<void, TaskError>[]>;
  queryOnlineEvent: (queryType: OnlineHistoryEventsQueryType, parent?: ActivityId) => Promise<Result<void, TaskError>>;
  resetOnlineWarnings: () => void;
}

export function useRefreshHandlers(): UseRefreshHandlersReturn {
  const { t } = useI18n({ useScope: 'global' });
  const { notifyError } = useNotifications();
  const { queryOnlineHistoryEvents } = useHistoryEventsApi();
  const { submitTask } = useNativeTask();
  const { queryAllExchangeEvents } = useExchangeEventsRefresh();
  const { addWarning, resetWarnings } = useSyncWarningsStore();
  const { enabled: isEth2Enabled } = useModuleEnabled(Module.ETH2);
  const { getApiKey } = useExternalApiKeys();
  const { authenticated: moneriumAuthenticated, refreshStatus } = useMoneriumOAuth();
  const { allowed: gnosisPayAllowed } = useFeatureAccess(PremiumFeature.GNOSIS_PAY);
  const { allowed: moneriumAllowed } = useFeatureAccess(PremiumFeature.MONERIUM);

  const queryTypeLabel = (queryType: OnlineHistoryEventsQueryType): string => {
    switch (queryType) {
      case OnlineHistoryEventsQueryType.BLOCK_PRODUCTIONS:
        return t('actions.online_events.query_type.block_productions');
      case OnlineHistoryEventsQueryType.ETH_WITHDRAWALS:
        return t('actions.online_events.query_type.eth_withdrawals');
      case OnlineHistoryEventsQueryType.GNOSIS_PAY:
        return t('actions.online_events.query_type.gnosis_pay');
      case OnlineHistoryEventsQueryType.MONERIUM:
        return t('actions.online_events.query_type.monerium');
    }
  };

  const buildMissingApiKeyMessage = (queryType: OnlineHistoryEventsQueryType): string => {
    const label = queryTypeLabel(queryType);
    if (queryType === OnlineHistoryEventsQueryType.BLOCK_PRODUCTIONS
      || queryType === OnlineHistoryEventsQueryType.ETH_WITHDRAWALS) {
      return t('actions.online_events.warning.missing_api_key.beaconchain', { queryType: label });
    }
    return t('actions.online_events.warning.missing_api_key.default', { queryType: label });
  };

  /**
   * Each online source is gated on its own precondition: eth2 on the module being enabled, gnosis pay
   * on being allowed and holding a key, monerium on being allowed and currently authenticated.
   */
  const canQueryOnlineEvent = async (queryType: OnlineHistoryEventsQueryType): Promise<boolean> => {
    const eth2QueryTypes: OnlineHistoryEventsQueryType[] = [
      OnlineHistoryEventsQueryType.ETH_WITHDRAWALS,
      OnlineHistoryEventsQueryType.BLOCK_PRODUCTIONS,
    ];

    if (!get(isEth2Enabled) && eth2QueryTypes.includes(queryType))
      return false;

    if (queryType === OnlineHistoryEventsQueryType.GNOSIS_PAY)
      return get(gnosisPayAllowed) && !!getApiKey('gnosis_pay');

    if (queryType === OnlineHistoryEventsQueryType.MONERIUM) {
      if (!get(moneriumAllowed))
        return false;

      await refreshStatus();
      return get(moneriumAuthenticated);
    }

    return true;
  };

  /**
   * Queries one online source as its own native activity.
   *
   * @remarks
   * A source the user has switched off or never authenticated resolves as {@link Skipped} rather
   * than a success: it submits no activity at all, so reporting it as one would let a refresh that
   * ran nothing look complete.
   */
  const queryOnlineEvent = async (queryType: OnlineHistoryEventsQueryType, parent?: ActivityId): Promise<Result<void, TaskError>> => {
    if (!(await canQueryOnlineEvent(queryType)))
      return err(Skipped({ message: t('actions.online_events.skipped.unavailable', { queryType: queryTypeLabel(queryType) }) }));

    logger.debug(`querying for ${queryType} events`);

    const outcome = await submitTask({
      id: onlineEventsActivityId(queryType),
      kind: ActivityKind.ONLINE_EVENTS,
      parent,
      rerunnable: true,
      run: async ({ runTask }): Promise<Result<void, TaskError>> => mapResult(
        await runTask<boolean>(
          async () => queryOnlineHistoryEvents({ asyncQuery: true, queryType }),
        ),
        () => {},
      ),
      subtitle: activityLabelFor(msg.$t('task_center.activity.online_events.refresh'), { queryType: queryTypeLabel(queryType) }),
      title: t('task_center.group.online_events'),
    });

    // The backend's ApiKeyMissingError rides on the tagged error's `cause`; narrow to read it.
    if (isErr(outcome) && isActionable(outcome.error)) {
      logger.error(outcome.error.message);
      if (outcome.error.cause instanceof ApiKeyMissingError) {
        addWarning({
          key: queryType,
          message: buildMissingApiKeyMessage(queryType),
          source: SyncWarningSource.ONLINE_EVENTS,
        });
      }
      else {
        notifyError(
          t('actions.online_events.error.title'),
          t('actions.online_events.error.description', {
            error: outcome.error.message,
            queryType,
          }),
        );
      }
    }
    logger.debug(`finished querying for ${queryType} events`);
    return outcome;
  };

  const resetOnlineWarnings = (): void => {
    resetWarnings();
  };

  return {
    queryAllExchangeEvents,
    queryOnlineEvent,
    resetOnlineWarnings,
  };
}

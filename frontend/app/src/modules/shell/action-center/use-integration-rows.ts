import type { ComputedRef } from 'vue';
import type { RouteLocationRaw } from 'vue-router';
import { toHumanReadable } from '@rotki/common';
import { externalLinks } from '@shared/external-links';
import { none, type Option, some } from 'plainfp/option';
import { getOr } from 'plainfp/records';
import { type MessageKey, msg } from '@/message-key';
import { type ActionItem, type ActionItemOption, type ActionTarget, ActionUrgency, applicable, createActionItem } from '@/modules/core/action-center/types';
import { getServiceRegisterUrl } from '@/modules/core/common/helpers/url';
import { useMoneriumOAuth } from '@/modules/integrations/monerium/use-monerium-auth';
import { ExternalServiceKeys, type ExternalServiceName } from '@/modules/integrations/types';
import { useExternalApiKeys } from '@/modules/settings/api-keys/external/use-external-api-keys';
import { SUPPRESSIBLE_SERVICES, SuppressibleMissingKeyService } from '@/modules/settings/types/user-settings';
import { useSetting } from '@/modules/settings/use-setting';
import { useSettingsOperations } from '@/modules/settings/use-settings-operations';
import { INDEXER_SETTINGS, useSuppressOption } from '@/modules/shell/action-center/row-options';
import { conditionRowId, type RaisedCondition, RaisedConditionKind, type RaisedConditionOf, useRaisedConditionsStore } from '@/modules/shell/action-center/use-raised-conditions-store';

type MissingApiKeyCondition = RaisedConditionOf<typeof RaisedConditionKind.MISSING_API_KEY>;

/** Services whose key only adds data: the queries work without one, so the row is a to-do, not a warning. */
const OPTIONAL_KEY_SERVICES: ReadonlySet<string> = new Set([SuppressibleMissingKeyService.BEACONCHAIN]);

/** Services that are transaction indexers, so reordering the indexers is an alternative to a key. */
const INDEXER_SERVICES: ReadonlySet<string> = new Set([
  SuppressibleMissingKeyService.BLOCKSCOUT,
  SuppressibleMissingKeyService.ETHERSCAN,
]);

/**
 * What a missing key costs, per service; any other service gets the generic description.
 *
 * @remarks
 * Etherscan ships with a packaged fallback key, so only it is slowed rather than skipped.
 */
const MISSING_KEY_DESCRIPTIONS: Readonly<Record<string, MessageKey>> = {
  [SuppressibleMissingKeyService.BEACONCHAIN]: msg.$t('action_center.rows.integrations.missing_api_key.description_beaconchain'),
  [SuppressibleMissingKeyService.BLOCKSCOUT]: msg.$t('action_center.rows.integrations.missing_api_key.description_blockscout'),
  [SuppressibleMissingKeyService.ETHERSCAN]: msg.$t('action_center.rows.integrations.missing_api_key.description_etherscan'),
  [SuppressibleMissingKeyService.HELIUS]: msg.$t('action_center.rows.integrations.missing_api_key.description_helius'),
  [SuppressibleMissingKeyService.THEGRAPH]: msg.$t('action_center.rows.integrations.missing_api_key.description_thegraph'),
};

const DEFAULT_MISSING_KEY_DESCRIPTION = msg.$t('action_center.rows.integrations.missing_api_key.description');

function isExternalServiceName(service: string): service is ExternalServiceName {
  return service in ExternalServiceKeys.shape;
}

function isSuppressibleService(service: string): service is SuppressibleMissingKeyService {
  return Array.prototype.includes.call(SUPPRESSIBLE_SERVICES, service);
}

/** The external services page, opened on the service the row is about. */
function serviceSettings(service: string): RouteLocationRaw {
  return { name: '/api-keys/external/', query: { service } };
}

/**
 * The integration rows: services a query needed a key for, and sessions that expired.
 *
 * @remarks
 * A missing key leaves as soon as a key is saved for the service or the service is suppressed, and a
 * Monerium session as soon as the status reads authenticated. A Gnosis Pay session has no status to
 * read, so its row stays until a verified sign-in clears the condition.
 */
export function useIntegrationRows(): ComputedRef<ActionItem[]> {
  const { t } = useI18n({ useScope: 'global' });

  const { conditions } = storeToRefs(useRaisedConditionsStore());
  const suppressedServices = useSetting('suppressMissingKeyMsgServices');
  const { getApiKey } = useExternalApiKeys();
  const { authenticated: moneriumAuthenticated } = useMoneriumOAuth();
  const { update } = useSettingsOperations();
  const { suppressOption } = useSuppressOption();

  function hasKey(service: string): boolean {
    return isExternalServiceName(service) && getApiKey(service) !== '';
  }

  function isSuppressed(service: string): boolean {
    return isSuppressibleService(service) && get(suppressedServices).includes(service);
  }

  async function suppress(service: SuppressibleMissingKeyService): Promise<void> {
    const current = get(suppressedServices);
    if (!current.includes(service))
      await update({ suppressMissingKeyMsgServices: [...current, service] });
  }

  /**
   * The alternatives to entering a key: another indexer order, where to get a key, the guide, and
   * silencing the service.
   *
   * @remarks
   * Etherscan is never offered a "get a key" link, since it keeps working on its packaged key.
   */
  function missingKeyOptions(service: string, serviceName: string): ActionItemOption[] {
    const external = getServiceRegisterUrl(service)?.external;
    return applicable<ActionItemOption>([
      INDEXER_SERVICES.has(service)
        ? some({ icon: 'lu-list-ordered', id: 'change-indexer-order', label: t('action_center.rows.integrations.missing_api_key.change_indexer_order'), target: INDEXER_SETTINGS })
        : none,
      external && service !== SuppressibleMissingKeyService.ETHERSCAN
        ? some({ icon: 'lu-external-link', id: 'get-key', label: t('action_center.rows.integrations.missing_api_key.get_key'), target: { kind: 'external', url: external } })
        : none,
      service === SuppressibleMissingKeyService.THEGRAPH
        ? some({ icon: 'lu-book-open', id: 'guide', label: t('action_center.rows.integrations.missing_api_key.guide'), target: { kind: 'external', url: externalLinks.usageGuideSection.theGraphApiKey } })
        : none,
      isSuppressibleService(service)
        ? some(suppressOption({
            confirmMessage: t('action_center.rows.integrations.missing_api_key.suppress_confirm.message', { service: serviceName }),
            confirmTitle: t('action_center.rows.integrations.missing_api_key.suppress_confirm.title'),
            label: t('action_center.rows.integrations.missing_api_key.do_not_show_again'),
            suppress: async () => suppress(service),
          }))
        : none,
    ]);
  }

  function missingKeyRow(condition: MissingApiKeyCondition): ActionItem {
    const { location, service } = condition;
    const serviceName = toHumanReadable(service, 'capitalize');
    const params = location
      ? { location: toHumanReadable(location, 'capitalize'), service: serviceName }
      : { service: serviceName };

    return createActionItem<ActionTarget, string>({
      actionLabel: t('action_center.rows.integrations.missing_api_key.action'),
      count: 1,
      description: t(getOr(MISSING_KEY_DESCRIPTIONS, service, DEFAULT_MISSING_KEY_DESCRIPTION), params),
      icon: 'lu-key-round',
      id: conditionRowId(condition),
      options: missingKeyOptions(service, serviceName),
      urgency: OPTIONAL_KEY_SERVICES.has(service) ? ActionUrgency.TODO : ActionUrgency.DECISION,
      target: { kind: 'route', to: getServiceRegisterUrl(service)?.route ?? serviceSettings(service) },
      title: location
        ? t('action_center.rows.integrations.missing_api_key.title_location', params)
        : t('action_center.rows.integrations.missing_api_key.title', params),
    });
  }

  function sessionRow(condition: RaisedCondition, service: ExternalServiceName, copy: { title: string; description: string }): ActionItem {
    return createActionItem<ActionTarget, string>({
      ...copy,
      actionLabel: t('external_services.actions.reauthenticate'),
      count: 1,
      icon: 'lu-log-in',
      id: conditionRowId(condition),
      urgency: ActionUrgency.DECISION,
      target: { kind: 'route', to: serviceSettings(service) },
    });
  }

  /** The row a condition raises right now, or none when it is resolved or belongs to another module. */
  function rowFor(condition: RaisedCondition): Option<ActionItem> {
    switch (condition.kind) {
      case RaisedConditionKind.MISSING_API_KEY:
        return hasKey(condition.service) || isSuppressed(condition.service) ? none : some(missingKeyRow(condition));
      case RaisedConditionKind.MONERIUM_SESSION:
        return get(moneriumAuthenticated)
          ? none
          : some(sessionRow(condition, 'monerium', {
              description: t('action_center.rows.integrations.monerium_session.description'),
              title: t('action_center.rows.integrations.monerium_session.title'),
            }));
      case RaisedConditionKind.GNOSIS_PAY_SESSION:
        return some(sessionRow(condition, 'gnosis_pay', {
          description: t('action_center.rows.integrations.gnosis_pay_session.description'),
          title: t('action_center.rows.integrations.gnosis_pay_session.title'),
        }));
      case RaisedConditionKind.NO_AVAILABLE_INDEXERS:
        return none;
    }
  }

  return computed<ActionItem[]>(() => applicable(get(conditions).map(rowFor)));
}

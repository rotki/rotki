import type { RouteLocationRaw } from 'vue-router';
import { toHumanReadable } from '@rotki/common';
import { externalLinks } from '@shared/external-links';
import { get } from '@vueuse/shared';
import { none, type Option, some } from 'plainfp/option';
import { getOr } from 'plainfp/records';
import { useI18n } from 'vue-i18n';
import { type MessageKey, msg } from '@/message-key';
import { type ActionItem, type ActionItemOption, type ActionTarget, ActionUrgency, applicable, createActionItem } from '@/modules/core/action-center/types';
import { getServiceRegisterUrl } from '@/modules/core/common/helpers/url';
import { ExternalServiceKeys, type ExternalServiceName } from '@/modules/integrations/types';
import { useExternalApiKeys } from '@/modules/settings/api-keys/external/use-external-api-keys';
import { SUPPRESSIBLE_SERVICES, SuppressibleMissingKeyService } from '@/modules/settings/types/user-settings';
import { useSetting } from '@/modules/settings/use-setting';
import { useSettingsOperations } from '@/modules/settings/use-settings-operations';
import { INDEXER_SETTINGS, useSuppressOption } from '@/modules/shell/action-center/row-options';
import { conditionRowId, type RaisedConditionKind, type RaisedConditionOf } from '@/modules/shell/action-center/use-raised-conditions-store';

type MissingApiKeyCondition = RaisedConditionOf<typeof RaisedConditionKind.MISSING_API_KEY>;

interface UseMissingKeyRowsReturn {
  /** The row of a missing or refused key, or none once a key is saved or the service is suppressed. */
  missingKeyRowFor: (condition: MissingApiKeyCondition) => Option<ActionItem>;
}

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
  [SuppressibleMissingKeyService.OPENSEA]: msg.$t('action_center.rows.integrations.missing_api_key.description_opensea'),
  [SuppressibleMissingKeyService.THEGRAPH]: msg.$t('action_center.rows.integrations.missing_api_key.description_thegraph'),
};

const DEFAULT_MISSING_KEY_DESCRIPTION = msg.$t('action_center.rows.integrations.missing_api_key.description');

/** What a refused key costs, per service that reports one. */
const REJECTED_KEY_DESCRIPTIONS: Readonly<Record<string, MessageKey>> = {
  [SuppressibleMissingKeyService.BLOCKSCOUT]: msg.$t('action_center.rows.integrations.missing_api_key.description_blockscout_rejected'),
  [SuppressibleMissingKeyService.OPENSEA]: msg.$t('action_center.rows.integrations.missing_api_key.description_opensea_rejected'),
  sochain: msg.$t('action_center.rows.integrations.missing_api_key.description_sochain_rejected'),
};

function isExternalServiceName(service: string): service is ExternalServiceName {
  return service in ExternalServiceKeys.shape;
}

function isSuppressibleService(service: string): service is SuppressibleMissingKeyService {
  return Array.prototype.includes.call(SUPPRESSIBLE_SERVICES, service);
}

/** The external services page, opened on the service the row is about. */
export function serviceSettings(service: string): RouteLocationRaw {
  return { name: '/api-keys/external/', query: { service } };
}

/**
 * The rows of services a query needed a key for, or whose key was refused.
 *
 * @remarks
 * A missing key leaves as soon as a key is saved for the service or the service is suppressed.
 */
export function useMissingKeyRows(): UseMissingKeyRowsReturn {
  const { t } = useI18n({ useScope: 'global' });

  const suppressedServices = useSetting('suppressMissingKeyMsgServices');
  const { getApiKey } = useExternalApiKeys();
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

  /** The title of a row: a refused key names where it was refused, a missing one where it was needed. */
  function missingKeyTitle({ keyRejected, location }: MissingApiKeyCondition, params: Record<string, string>): string {
    if (keyRejected && location)
      return t('action_center.rows.integrations.missing_api_key.title_rejected', params);
    return location
      ? t('action_center.rows.integrations.missing_api_key.title_location', params)
      : t('action_center.rows.integrations.missing_api_key.title', params);
  }

  function missingKeyRow(condition: MissingApiKeyCondition): ActionItem {
    const { keyRejected, location, service } = condition;
    const serviceName = toHumanReadable(service, 'capitalize');
    const params: Record<string, string> = location
      ? { location: toHumanReadable(location, 'capitalize'), service: serviceName }
      : { service: serviceName };
    const description = keyRejected
      ? getOr(REJECTED_KEY_DESCRIPTIONS, service, DEFAULT_MISSING_KEY_DESCRIPTION)
      : getOr(MISSING_KEY_DESCRIPTIONS, service, DEFAULT_MISSING_KEY_DESCRIPTION);

    return createActionItem<ActionTarget, string>({
      actionLabel: t('action_center.rows.integrations.missing_api_key.action'),
      count: 1,
      description: t(description, params),
      icon: 'lu-key-round',
      id: conditionRowId(condition),
      options: missingKeyOptions(service, serviceName),
      urgency: OPTIONAL_KEY_SERVICES.has(service) ? ActionUrgency.TODO : ActionUrgency.DECISION,
      target: { kind: 'route', to: getServiceRegisterUrl(service)?.route ?? serviceSettings(service) },
      title: missingKeyTitle(condition, params),
    });
  }

  /**
   * Whether a missing key's row is still open.
   *
   * @remarks
   * A refused key is saved by definition, so having a key does not close its row; saving a new key
   * clears the condition instead.
   */
  function isMissingKeyOpen({ keyRejected, service }: MissingApiKeyCondition): boolean {
    return !isSuppressed(service) && (keyRejected === true || !hasKey(service));
  }

  function missingKeyRowFor(condition: MissingApiKeyCondition): Option<ActionItem> {
    return isMissingKeyOpen(condition) ? some(missingKeyRow(condition)) : none;
  }

  return { missingKeyRowFor };
}

import type { EventPriceUpdatePayload } from '@/modules/history/events/prices/use-event-price-update-trigger';
import type { GroupEventData, StandaloneEventData } from '@/modules/history/management/forms/form-types';
import { get, set } from '@vueuse/shared';
import { computed, type ComputedRef, readonly, ref, type Ref, shallowRef } from 'vue';
import { useI18n } from 'vue-i18n';
import { useRouter } from 'vue-router';
import { useIgnoredAssetOperations } from '@/modules/assets/use-ignored-asset-operations';
import { useAssetMovementMatchingApi } from '@/modules/history/api/events/use-asset-movement-matching-api';
import { useHistoryIgnoringApi } from '@/modules/history/api/use-history-ignoring-api';
import {
  type DataIssue,
  IncompleteSwapPayload,
  UnmatchedExchangeTransferPayload,
} from '@/modules/history/data-issues/schemas';
import { describeIssue, relatedEventRoute } from '@/modules/history/data-issues/transforms';
import { useDataIssues } from '@/modules/history/data-issues/use-data-issues';
import { PremiumFeature, useFeatureAccess } from '@/modules/premium/use-feature-access';
import { type NamedFailure, useFailureSlot } from '@/modules/shell/components/named-failure';

export type InlineRemediationAction =
  | 'add_acquisition'
  | 'auto_match_exchange_transfer'
  | 'confirm_zero_basis'
  | 'dismiss_as_standalone'
  | 'edit_event'
  | 'ignore_asset'
  | 'ignore_group'
  | 'match_transfer'
  | 'resolve_as_external'
  | 'set_manual_price'
  | 'unignore_asset';

export interface RemediationRequest {
  readonly action: InlineRemediationAction;
  readonly issue: DataIssue;
}

interface UseDataIssueRemediationActionsReturn {
  actionFailure: Readonly<Ref<NamedFailure | undefined>>;
  busy: Readonly<Ref<boolean>>;
  clearFailure: () => void;
  hasModalOpen: ComputedRef<boolean>;
  modelEventForm: Ref<GroupEventData | StandaloneEventData | undefined>;
  modelMatchingOpen: Ref<boolean>;
  modelPriceUpdate: Ref<EventPriceUpdatePayload | undefined>;
  modelSubModalOpen: Ref<boolean>;
  onModalSaved: () => Promise<void>;
  runRemediation: (request: RemediationRequest) => Promise<void>;
}

function issueEventId(issue: DataIssue): number | undefined {
  return issue.eventIdentifier ?? describeIssue(issue).eventIdentifier;
}

function issueGroupId(issue: DataIssue): string | undefined {
  if (issue.groupIdentifier)
    return issue.groupIdentifier;
  const raw = issue.payload?.groupIdentifier;
  return typeof raw === 'string' && raw.length > 0 ? raw : undefined;
}

function excludedSwapAssets(issue: DataIssue): string[] {
  const parsed = IncompleteSwapPayload.safeParse(issue.payload);
  if (parsed.success && parsed.data.excludedAssets.length > 0)
    return parsed.data.excludedAssets;
  return issue.asset ? [issue.asset] : [];
}

function unmatchedTransferEventId(issue: DataIssue): number | undefined {
  if (issue.eventIdentifier !== null)
    return issue.eventIdentifier;
  const parsed = UnmatchedExchangeTransferPayload.safeParse(issue.payload);
  return parsed.success ? parsed.data.eventIdentifier : undefined;
}

/**
 * Runs inline remediation actions for PnL data issues, reusing existing modals (price update,
 * history event form, asset-movement matching) and APIs (ignore asset/group, manual confirmation,
 * external transfer resolution, auto-remediation retry).
 */
export function useDataIssueRemediationActions(
  reload: () => Promise<void>,
): UseDataIssueRemediationActionsReturn {
  const { t } = useI18n({ useScope: 'global' });
  const router = useRouter();
  const { resolveManually, retry } = useDataIssues();
  const { ignoreAsset, unignoreAsset } = useIgnoredAssetOperations();
  const { ignoreActions } = useHistoryIgnoringApi();
  const { matchAssetMovements } = useAssetMovementMatchingApi();
  const { allowed: matchingAllowed } = useFeatureAccess(PremiumFeature.ASSET_MOVEMENT_MATCHING);

  const busy = shallowRef<boolean>(false);
  const modelPriceUpdate = ref<EventPriceUpdatePayload>();
  const modelEventForm = ref<GroupEventData | StandaloneEventData>();
  const modelMatchingOpen = shallowRef<boolean>(false);
  const modelSubModalOpen = shallowRef<boolean>(false);
  const { clear: clearFailure, failure: actionFailure, report: reportFailure } = useFailureSlot();

  const hasModalOpen = computed<boolean>(
    () => get(modelPriceUpdate) !== undefined
      || get(modelEventForm) !== undefined
      || get(modelMatchingOpen)
      || get(modelSubModalOpen),
  );

  async function withBusy(title: string, work: () => Promise<boolean>): Promise<void> {
    set(busy, true);
    clearFailure();
    try {
      if (await work())
        await reload();
    }
    catch (error: unknown) {
      reportFailure(title, error);
    }
    finally {
      set(busy, false);
    }
  }

  async function runDisposition(issue: DataIssue, disposition: string, errorTitle: string): Promise<void> {
    await withBusy(errorTitle, async () => {
      const result = await resolveManually(issue.id, undefined, disposition);
      if (!result.ok) {
        reportFailure(errorTitle, result.error);
        return false;
      }
      return true;
    });
  }

  const handlers: Record<InlineRemediationAction, (issue: DataIssue) => Promise<void>> = {
    add_acquisition: async () => {
      set(modelEventForm, { nextSequenceId: '0', type: 'add' });
    },
    auto_match_exchange_transfer: async (issue) => {
      const title = t('data_issues.action.retry.error');
      await withBusy(title, async () => {
        const result = await retry(issue.id);
        if (!result.ok) {
          reportFailure(title, result.error);
          return false;
        }
        return true;
      });
    },
    confirm_zero_basis: async (issue) => {
      await runDisposition(issue, 'confirm_zero_basis', t('data_issues.inline_actions.error.confirm_zero_basis'));
    },
    dismiss_as_standalone: async (issue) => {
      await runDisposition(issue, 'dismiss_as_standalone', t('data_issues.inline_actions.error.dismiss_as_standalone'));
    },
    edit_event: async (issue) => {
      const link = relatedEventRoute(issue.kind, issueEventId(issue), issueGroupId(issue), issue.asset);
      if (link)
        await router.push(link);
    },
    ignore_asset: async (issue) => {
      if (!issue.asset)
        return;
      const asset = issue.asset;
      const title = t('data_issues.inline_actions.error.ignore_asset');
      await withBusy(title, async () => {
        const outcome = await ignoreAsset(asset);
        if (!outcome.success) {
          reportFailure(title, outcome.message ?? '');
          return false;
        }
        return true;
      });
    },
    ignore_group: async (issue) => {
      const groupId = issueGroupId(issue);
      if (!groupId)
        return;
      await withBusy(t('data_issues.inline_actions.error.ignore_group'), async () => {
        await ignoreActions({ data: [groupId] });
        return true;
      });
    },
    match_transfer: async () => {
      set(modelMatchingOpen, true);
    },
    resolve_as_external: async (issue) => {
      if (!get(matchingAllowed))
        return;
      const eventId = unmatchedTransferEventId(issue);
      if (eventId === undefined)
        return;
      await withBusy(t('data_issues.inline_actions.error.resolve_as_external'), async () => {
        await matchAssetMovements(eventId, undefined, true);
        return true;
      });
    },
    set_manual_price: async (issue) => {
      if (!issue.asset)
        return;
      set(modelPriceUpdate, { asset: issue.asset, timestamp: issue.tsEnd || issue.tsStart });
    },
    unignore_asset: async (issue) => {
      const assets = excludedSwapAssets(issue);
      if (assets.length === 0)
        return;
      const title = t('data_issues.inline_actions.error.unignore_asset');
      await withBusy(title, async () => {
        const outcome = await unignoreAsset(assets);
        if (!outcome.success) {
          reportFailure(title, outcome.message ?? '');
          return false;
        }
        return true;
      });
    },
  };

  async function onModalSaved(): Promise<void> {
    await reload();
  }

  async function runRemediation({ action, issue }: RemediationRequest): Promise<void> {
    clearFailure();
    await handlers[action](issue);
  }

  return {
    actionFailure,
    busy: readonly(busy),
    clearFailure,
    hasModalOpen,
    modelEventForm,
    modelMatchingOpen,
    modelPriceUpdate,
    modelSubModalOpen,
    onModalSaved,
    runRemediation,
  };
}

import type { RuiIcons } from '@rotki/ui-library';
import { startPromise } from '@shared/utils';
import { useReportIssue } from '@/modules/core/common/use-report-issue';
import { UserMessageKey } from '@/modules/core/messaging/types/base';
import { type BackendProblem, BALANCE_SNAPSHOT, type ProblemItem } from '@/modules/core/notifications/problems/backend-problem-tree';
import { useBackendProblemText } from '@/modules/core/notifications/problems/use-backend-problem-text';

export interface ProblemItemAction {
  readonly label: string;
  readonly icon: RuiIcons;
  readonly run: () => void;
}

interface UseBackendProblemActionsReturn {
  /** What the user can do about an item, or undefined when there is nothing to do but wait. */
  itemAction: (problem: BackendProblem, item: ProblemItem) => ProblemItemAction | undefined;
}

/**
 * The one action each backend problem item offers, by family.
 *
 * @remarks
 * A missing price opens the price manager's add dialog for that asset, at the time it was missing
 * or, for a current price, on the latest prices. Unreadable data, a broken local entry and an
 * internal error can only be reported. A network failure, an unsupported feature and a failed
 * snapshot offer nothing: they pass or wait on rotki.
 */
export function useBackendProblemActions(): UseBackendProblemActionsReturn {
  const { t } = useI18n({ useScope: 'global' });
  const router = useRouter();
  const { show: showReportIssue } = useReportIssue();
  const { itemDetails, problemTitle } = useBackendProblemText();

  function addPrice(asset: string, timestamp: number | null): ProblemItemAction {
    return {
      icon: 'lu-plus',
      label: t('backend_problems.actions.add_price'),
      run: (): void => {
        startPromise(router.push(timestamp === null
          ? { name: '/price-manager/latest/', query: { add: 'true', fromAsset: asset } }
          : { name: '/price-manager/historic/', query: { add: 'true', fromAsset: asset, timestamp: String(timestamp) } }));
      },
    };
  }

  function reportIssue(problem: BackendProblem, item: ProblemItem): ProblemItemAction {
    return {
      icon: 'lu-bug',
      label: t('backend_problems.actions.report_issue'),
      run: (): void => showReportIssue({ description: itemDetails(item), title: problemTitle(problem) }),
    };
  }

  function itemAction(problem: BackendProblem, item: ProblemItem): ProblemItemAction | undefined {
    const { source } = item;
    switch (source.key) {
      case UserMessageKey.PRICE:
        return source.fields.asset ? addPrice(source.fields.asset, source.fields.timestamp) : undefined;
      case UserMessageKey.BAD_DATA:
      case UserMessageKey.INTERNAL:
      case UserMessageKey.LOCAL_DB:
        return reportIssue(problem, item);
      case BALANCE_SNAPSHOT:
      case UserMessageKey.NETWORK:
      case UserMessageKey.UNKNOWN_ASSET:
      case UserMessageKey.UNSUPPORTED:
        return undefined;
    }
  }

  return { itemAction };
}

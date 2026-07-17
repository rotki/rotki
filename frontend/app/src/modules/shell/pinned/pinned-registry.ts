import type { Component } from 'vue';
import { type MessageKey, msg } from '@/message-key';
import { type PinnedName, PinnedNames } from '@/modules/session/types';

/**
 * Registry entry for a pinnable panel. Central mapping from a `PinnedName` to the
 * component rendered in the pinned rail plus the metadata the multi-slot tab strip
 * needs (label + icon). Replaces the per-host if-chain that used to live in
 * `PinnedSidebar.vue`; keep it the single source of truth for the pinned mechanism.
 */
export interface PinnedPanelDef {
  /** Lazily-loaded host component (`*Pinned.vue`) rendered when this panel is active. */
  component: Component;
  /** Branded i18n key for the tab label, resolved later with `t(labelKey)`. */
  labelKey: MessageKey;
  /** RuiIcons name shown on the tab. */
  icon: string;
  /** Optional panel-specific controls rendered on the rail's tab strip for the active panel. */
  actions?: Component;
  /** Whether the panel can be re-pinned from persistence with empty props on reload.
   * Panels that need live context (e.g. the report card needs a generated report)
   * opt out with `false`; the rest fetch their own data and restore safely. Defaults to true. */
  restorable?: boolean;
}

export const PINNED_PANELS: Record<PinnedName, PinnedPanelDef> = {
  [PinnedNames.BALANCE_DIVERGENCE]: {
    component: defineAsyncComponent(async () => import('@/modules/history/balances/BalanceDivergencePinned.vue')),
    icon: 'lu-search',
    labelKey: msg.$t('balance_divergence.title'),
  },
  [PinnedNames.DATA_ISSUES]: {
    component: defineAsyncComponent(async () => import('@/modules/history/data-issues/components/DataIssuesPinned.vue')),
    icon: 'lu-shield-alert',
    labelKey: msg.$t('data_issues.panel.title'),
  },
  [PinnedNames.INTERNAL_TX_CONFLICTS]: {
    actions: defineAsyncComponent(async () => import('@/modules/history/internal-tx-conflicts/InternalTxConflictsActions.vue')),
    component: defineAsyncComponent(async () => import('@/modules/history/internal-tx-conflicts/InternalTxConflictsPinned.vue')),
    icon: 'lu-git-merge',
    labelKey: msg.$t('internal_tx_conflicts.pinned.title'),
  },
  [PinnedNames.MATCH_ASSET_MOVEMENTS]: {
    component: defineAsyncComponent(async () => import('@/modules/history/events/MatchAssetMovementsPinned.vue')),
    icon: 'lu-repeat',
    labelKey: msg.$t('asset_movement_matching.dialog.title'),
  },
  [PinnedNames.REPORT_ACTIONABLE_CARD]: {
    component: defineAsyncComponent(async () => import('@/modules/reports/ReportActionableCard.vue')),
    icon: 'lu-triangle-alert',
    labelKey: msg.$t('profit_loss_report.actionable.show_issues'),
    // Needs a live generated report; cannot be restored from persistence with empty props.
    restorable: false,
  },
};

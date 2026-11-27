<script setup lang="ts">
import type { InlineRemediationAction, RemediationRequest } from '@/modules/history/data-issues/use-data-issue-remediation-actions';
import { RuiButton, RuiIcon, type RuiIcons, RuiTooltip } from '@rotki/ui-library';
import { get } from '@vueuse/shared';
import { computed } from 'vue';
import { useI18n } from 'vue-i18n';
import { canResolveManually, canRetry, IssueKind } from '@/modules/history/data-issues/constants';
import { type DataIssue, IncompleteSwapPayload } from '@/modules/history/data-issues/schemas';
import { PremiumFeature, useFeatureAccess } from '@/modules/premium/use-feature-access';

const { busy = false, compact = false, issue } = defineProps<{
  issue: DataIssue;
  busy?: boolean;
  compact?: boolean;
}>();

const emit = defineEmits<{
  action: [request: RemediationRequest];
}>();

interface ActionButtonSpec {
  readonly action: InlineRemediationAction;
  readonly disabled?: boolean;
  readonly icon: RuiIcons;
  readonly label: string;
  readonly primary?: boolean;
  readonly tooltip?: string;
}

const { t } = useI18n({ useScope: 'global' });
const { allowed: matchingAllowed } = useFeatureAccess(PremiumFeature.ASSET_MOVEMENT_MATCHING);

function groupIdentifierOf(target: DataIssue): string | undefined {
  if (target.groupIdentifier)
    return target.groupIdentifier;
  const raw = target.payload?.groupIdentifier;
  return typeof raw === 'string' && raw.length > 0 ? raw : undefined;
}

function missingPriceButtons(target: DataIssue): ActionButtonSpec[] {
  const list: ActionButtonSpec[] = target.asset
    ? [
        { action: 'set_manual_price', icon: 'lu-dollar-sign', label: t('data_issues.inline_actions.set_price'), primary: true },
        { action: 'ignore_asset', icon: 'lu-eye-off', label: t('data_issues.inline_actions.ignore_asset') },
      ]
    : [];
  if (groupIdentifierOf(target))
    list.push({ action: 'ignore_group', icon: 'lu-archive', label: t('data_issues.inline_actions.ignore_event') });
  return list;
}

function missingCostBasisButtons(): ActionButtonSpec[] {
  return [
    { action: 'add_acquisition', icon: 'lu-plus', label: t('data_issues.inline_actions.add_acquisition'), primary: true },
    { action: 'match_transfer', icon: 'lu-link', label: t('data_issues.inline_actions.match_transfer') },
    { action: 'confirm_zero_basis', icon: 'lu-check', label: t('data_issues.inline_actions.confirm_zero_basis') },
  ];
}

function incompleteSwapButtons(target: DataIssue): ActionButtonSpec[] {
  const parsed = IncompleteSwapPayload.safeParse(target.payload);
  const canUnignore = parsed.success
    && parsed.data.missingOrExcludedReason === 'ignored_asset'
    && parsed.data.excludedAssets.length > 0;

  const list: ActionButtonSpec[] = [];
  if (canUnignore)
    list.push({ action: 'unignore_asset', icon: 'lu-eye', label: t('data_issues.inline_actions.unignore_asset'), primary: true });
  if (groupIdentifierOf(target))
    list.push({ action: 'ignore_group', icon: 'lu-archive', label: t('data_issues.inline_actions.ignore_group'), primary: !canUnignore });
  list.push(
    { action: 'edit_event', icon: 'lu-pencil', label: t('data_issues.inline_actions.edit_event') },
    { action: 'dismiss_as_standalone', icon: 'lu-check', label: t('data_issues.inline_actions.process_standalone') },
  );
  return list;
}

function unmatchedTransferButtons(target: DataIssue): ActionButtonSpec[] {
  const retryButton: ActionButtonSpec[] = canRetry(target.kind, target.state)
    ? [{ action: 'auto_match_exchange_transfer', icon: 'lu-refresh-ccw', label: t('data_issues.inline_actions.auto_match') }]
    : [];
  const externalDisabled = !get(matchingAllowed);
  return [
    ...retryButton,
    { action: 'match_transfer', icon: 'lu-link', label: t('data_issues.inline_actions.match_transfer'), primary: true },
    {
      action: 'resolve_as_external',
      disabled: externalDisabled,
      icon: 'lu-external-link',
      label: t('data_issues.inline_actions.mark_external'),
      tooltip: externalDisabled ? t('data_issues.inline_actions.premium_required') : undefined,
    },
  ];
}

const buttons = computed<ActionButtonSpec[]>(() => {
  if (!canResolveManually(issue.state))
    return [];

  switch (issue.kind) {
    case IssueKind.MISSING_PRICE:
      return missingPriceButtons(issue);
    case IssueKind.MISSING_COST_BASIS:
      return missingCostBasisButtons();
    case IssueKind.INCOMPLETE_SWAP:
      return incompleteSwapButtons(issue);
    case IssueKind.UNMATCHED_EXCHANGE_TRANSFER:
      return unmatchedTransferButtons(issue);
    default:
      return [];
  }
});
</script>

<template>
  <div
    v-if="buttons.length > 0"
    class="flex flex-wrap items-center gap-1.5"
    data-testid="data-issue-inline-actions"
  >
    <RuiTooltip
      v-for="item in buttons"
      :key="item.action"
      :disabled="!item.tooltip"
      :open-delay="300"
    >
      <template #activator>
        <RuiButton
          :size="compact ? 'xs' : 'sm'"
          :variant="item.primary ? undefined : 'outlined'"
          :color="item.primary ? 'primary' : undefined"
          :disabled="busy || item.disabled"
          :data-testid="`data-issue-inline-${item.action}`"
          @click.stop="emit('action', { action: item.action, issue })"
        >
          <template #prepend>
            <RuiIcon
              :name="item.icon"
              size="14"
            />
          </template>
          {{ item.label }}
        </RuiButton>
      </template>
      {{ item.tooltip }}
    </RuiTooltip>
  </div>
</template>

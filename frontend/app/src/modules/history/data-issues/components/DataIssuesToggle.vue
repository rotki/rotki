<script setup lang="ts">
import { startPromise } from '@shared/utils';
import { useDataIssuesSummary } from '@/modules/history/data-issues/use-data-issues-summary';
import { PinnedNames } from '@/modules/session/types';
import { usePinnedPanel } from '@/modules/shell/pinned/use-pinned-panel';
import { useSyncCompleted } from '@/modules/shell/sync-progress/use-sync-completed';

const { t } = useI18n({ useScope: 'global' });

const { actionableCount, refreshSummary } = useDataIssuesSummary();
const { isPinned, toggle: togglePanel } = usePinnedPanel(PinnedNames.DATA_ISSUES);
const { syncCompleted } = useSyncCompleted();

const active = isPinned;

function toggle(): void {
  // The inbox lives only in the pinned rail now: pin it (and focus/reveal) or close it.
  togglePanel({});
}

// Keep the badge count in step with the inbox: refresh when the history sync finishes.
watch(syncCompleted, () => {
  startPromise(refreshSummary());
});

onMounted(refreshSummary);
</script>

<template>
  <RuiTooltip :open-delay="300">
    <template #activator>
      <RuiBadge
        :model-value="actionableCount > 0"
        :text="actionableCount.toString()"
        color="error"
        placement="top"
        size="sm"
        offset-y="6"
        offset-x="-4"
      >
        <RuiButton
          variant="outlined"
          color="primary"
          size="sm"
          :class="{ '!bg-rui-primary !text-white': active }"
          data-testid="data-issues-toggle"
          @click="toggle()"
        >
          <RuiIcon
            name="lu-shield-alert"
            size="16"
          />
        </RuiButton>
      </RuiBadge>
    </template>
    {{ t('data_issues.toggle.tooltip') }}
  </RuiTooltip>
</template>

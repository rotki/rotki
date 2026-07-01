<script setup lang="ts">
import { useAreaVisibilityStore } from '@/modules/core/common/use-area-visibility-store';
import { useDataIssuesInboxStore } from '@/modules/history/data-issues/use-data-issues-inbox-store';
import { useDataIssuesSummary } from '@/modules/history/data-issues/use-data-issues-summary';
import { PinnedNames } from '@/modules/session/types';

const { t } = useI18n({ useScope: 'global' });

const { actionableCount, refreshSummary } = useDataIssuesSummary();
const { pinned } = storeToRefs(useAreaVisibilityStore());
const { overlayVisible } = storeToRefs(useDataIssuesInboxStore());

const isPinned = computed<boolean>(() => get(pinned)?.name === PinnedNames.DATA_ISSUES);
const active = computed<boolean>(() => get(overlayVisible) || get(isPinned));

function toggle(): void {
  // While the panel lives in the pinned rail, the toggle closes it there instead of
  // opening a second overlay copy.
  if (get(isPinned)) {
    set(pinned, null);
    return;
  }
  set(overlayVisible, !get(overlayVisible));
}

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

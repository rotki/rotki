<script setup lang="ts">
import type { RouteLocationRaw } from 'vue-router';
import type { DataIssue } from '@/modules/history/data-issues/schemas';
import {
  canDismiss,
  canResolveManually,
  canRetry,
  IssueState,
} from '@/modules/history/data-issues/constants';
import ConfirmPopover from '@/modules/shell/components/ConfirmPopover.vue';

const { issue, eventRoute } = defineProps<{
  issue: DataIssue;
  eventRoute?: RouteLocationRaw;
}>();

const emit = defineEmits<{
  goto: [route: RouteLocationRaw];
  dismiss: [issue: DataIssue];
  retry: [issue: DataIssue];
  resolve: [issue: DataIssue];
}>();

const { t } = useI18n({ useScope: 'global' });

function onGoto(): void {
  if (eventRoute)
    emit('goto', eventRoute);
}
</script>

<template>
  <div class="flex items-center gap-0.5">
    <RuiTooltip
      v-if="eventRoute"
      :open-delay="300"
    >
      <template #activator>
        <RuiButton
          variant="text"
          icon
          size="sm"
          :aria-label="t('data_issues.panel.goto_event')"
          data-testid="data-issues-panel-goto-event"
          @click.stop="onGoto()"
        >
          <RuiIcon
            name="lu-arrow-up-right"
            size="16"
          />
        </RuiButton>
      </template>
      {{ t('data_issues.panel.goto_event') }}
    </RuiTooltip>
    <span
      v-if="canDismiss(issue.state)"
      class="contents"
      @click.stop
    >
      <ConfirmPopover
        tone="warning"
        :title="t('data_issues.action.dismiss.confirm.title')"
        :message="t('data_issues.action.dismiss.confirm.message')"
        :confirm-label="t('data_issues.action.dismiss.label')"
        @confirm="emit('dismiss', issue)"
      >
        <template #activator="{ attrs }">
          <RuiButton
            variant="text"
            icon
            size="sm"
            :title="t('data_issues.action.dismiss.label')"
            :aria-label="t('data_issues.action.dismiss.label')"
            data-testid="data-issues-panel-dismiss"
            v-bind="attrs"
          >
            <RuiIcon
              name="lu-archive"
              size="16"
            />
          </RuiButton>
        </template>
      </ConfirmPopover>
    </span>
    <RuiTooltip
      v-if="canRetry(issue.kind, issue.state) || issue.state === IssueState.AUTO_REMEDIATING"
      :open-delay="300"
    >
      <template #activator>
        <RuiButton
          variant="text"
          icon
          size="sm"
          :aria-label="t('data_issues.action.retry.label')"
          data-testid="data-issues-panel-retry"
          :disabled="!canRetry(issue.kind, issue.state)"
          @click.stop="emit('retry', issue)"
        >
          <RuiIcon
            name="lu-refresh-ccw"
            size="16"
          />
        </RuiButton>
      </template>
      {{ t('data_issues.action.retry.label') }}
    </RuiTooltip>
    <RuiTooltip
      v-if="canResolveManually(issue.state)"
      :open-delay="300"
    >
      <template #activator>
        <RuiButton
          variant="text"
          icon
          size="sm"
          color="primary"
          :aria-label="t('data_issues.action.resolve.label')"
          data-testid="data-issues-panel-resolve"
          @click.stop="emit('resolve', issue)"
        >
          <RuiIcon
            name="lu-check"
            size="16"
          />
        </RuiButton>
      </template>
      {{ t('data_issues.action.resolve.label') }}
    </RuiTooltip>
  </div>
</template>

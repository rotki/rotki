<script setup lang="ts">
import type { DataIssue } from '@/modules/history/data-issues/schemas';
import type { ConfirmQuestion } from '@/modules/shell/components/confirm-question';
import type { NamedFailure } from '@/modules/shell/components/named-failure';
import { canDismiss, canResolveManually, canRetry, IssueState } from '@/modules/history/data-issues/constants';
import FailureStrip from '@/modules/shell/components/FailureStrip.vue';
import InlineConfirm from '@/modules/shell/components/InlineConfirm.vue';

/**
 * The issue's actions, under its detail.
 *
 * @remarks
 * Dismiss asks in place of the buttons before it emits. A failed dismiss or retry is named above
 * them without a retry of its own, the button being the retry.
 */
const { issue, busy = false, failure } = defineProps<{
  issue: DataIssue;
  busy?: boolean;
  failure?: NamedFailure;
}>();

const emit = defineEmits<{
  dismiss: [id: number];
  retry: [id: number];
  resolve: [id: number];
}>();

const { t } = useI18n({ useScope: 'global' });

const askingDismiss = ref<boolean>(false);

const dismissQuestion = computed<ConfirmQuestion>(() => ({
  confirmLabel: t('data_issues.action.dismiss.label'),
  message: t('data_issues.action.dismiss.confirm.message'),
  title: t('data_issues.action.dismiss.confirm.title'),
}));

function confirmDismiss(): void {
  set(askingDismiss, false);
  emit('dismiss', issue.id);
}

watch(() => issue.id, () => {
  set(askingDismiss, false);
});
</script>

<template>
  <div class="flex flex-col gap-2 p-4 border-t border-rui-divider">
    <FailureStrip
      v-if="failure"
      :title="failure.title"
      :failure="failure.failure"
      data-testid="data-issue-detail-failure"
    />
    <InlineConfirm
      v-if="askingDismiss"
      :question="dismissQuestion"
      @cancel="askingDismiss = false"
      @confirm="confirmDismiss()"
    />
    <div
      v-else
      class="flex items-center justify-end gap-2"
    >
      <RuiButton
        variant="outlined"
        :disabled="busy || !canDismiss(issue.state)"
        data-testid="data-issue-detail-dismiss"
        @click="askingDismiss = true"
      >
        {{ t('data_issues.action.dismiss.label') }}
      </RuiButton>
      <RuiButton
        v-if="canRetry(issue.kind, issue.state) || issue.state === IssueState.AUTO_REMEDIATING"
        variant="outlined"
        color="primary"
        :disabled="busy || !canRetry(issue.kind, issue.state)"
        data-testid="data-issue-detail-retry"
        @click="emit('retry', issue.id)"
      >
        {{ t('data_issues.action.retry.label') }}
      </RuiButton>
      <RuiButton
        color="primary"
        :disabled="busy || !canResolveManually(issue.state)"
        data-testid="data-issue-detail-resolve"
        @click="emit('resolve', issue.id)"
      >
        {{ t('data_issues.action.resolve.label') }}
      </RuiButton>
    </div>
  </div>
</template>

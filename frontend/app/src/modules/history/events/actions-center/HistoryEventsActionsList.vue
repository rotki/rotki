<script setup lang="ts">
import { startPromise } from '@shared/utils';
import HistoryEventsActionRow from '@/modules/history/events/actions-center/HistoryEventsActionRow.vue';
import { type HistoryEventIssue, type HistoryIssueTarget, useHistoryEventIssues } from '@/modules/history/events/actions-center/use-history-event-issues';

const emit = defineEmits<{
  open: [target: HistoryIssueTarget];
}>();

const { t } = useI18n({ useScope: 'global' });

const { activeIssues, categoryCount, checking, clearedIssues, hasIssues, lockedIssues, refreshAll, refreshing, reviewIssues } = useHistoryEventIssues();

// Locked and ignored-only rows sit under the actionable ones: their counts are
// real information, but neither asks the user to do something right now.
const rows = computed<HistoryEventIssue[]>(() => [...get(activeIssues), ...get(reviewIssues), ...get(lockedIssues)]);

const title = computed<string>(() => {
  if (get(hasIssues))
    return t('transactions.alerts.title');
  return get(checking) ? t('transactions.alerts.title_checking') : t('transactions.alerts.title_clear');
});

const subtitle = computed<string>(() => {
  if (get(hasIssues))
    return t('transactions.alerts.subtitle', { count: get(categoryCount) }, get(categoryCount));
  return get(checking) ? t('transactions.alerts.subtitle_checking') : t('transactions.alerts.subtitle_clear');
});
</script>

<template>
  <div
    class="relative"
    data-testid="actions-center-panel"
  >
    <RuiProgress
      v-if="refreshing"
      thickness="2"
      color="primary"
      variant="indeterminate"
      class="absolute top-0 left-0 w-full"
    />

    <div class="flex items-center gap-2 px-4 py-3 border-b border-default">
      <div class="flex-1 min-w-0">
        <h6 class="text-body-1 font-medium text-rui-text">
          {{ title }}
        </h6>
        <p class="text-caption text-rui-text-secondary">
          {{ subtitle }}
        </p>
      </div>

      <RuiButton
        variant="text"
        size="sm"
        :loading="refreshing"
        data-testid="actions-center-rescan"
        @click="startPromise(refreshAll())"
      >
        <template #prepend>
          <RuiIcon
            name="lu-refresh-ccw"
            size="16"
          />
        </template>
        {{ t('transactions.alerts.rescan') }}
      </RuiButton>
    </div>

    <div
      v-if="rows.length > 0"
      class="px-4 divide-y divide-rui-grey-200 dark:divide-rui-grey-800"
    >
      <HistoryEventsActionRow
        v-for="issue in rows"
        :key="issue.id"
        :issue="issue"
        @action="emit('open', $event.target)"
      />
    </div>

    <div
      v-if="!checking && clearedIssues.length > 0"
      class="flex flex-wrap items-center gap-x-4 gap-y-1 px-4 py-3 bg-rui-grey-50 dark:bg-rui-grey-900"
      data-testid="actions-center-cleared"
    >
      <span class="text-caption text-rui-text-disabled">
        {{ t('transactions.alerts.cleared') }}
      </span>
      <button
        v-for="issue in clearedIssues"
        :key="issue.id"
        type="button"
        class="flex items-center gap-1.5 text-caption text-rui-text-secondary hover:text-rui-text hover:underline"
        :data-testid="`actions-center-cleared-${issue.id}`"
        @click="emit('open', issue.checkTarget)"
      >
        <RuiIcon
          name="lu-circle-check"
          size="14"
          color="success"
        />
        {{ issue.title }}
      </button>
    </div>
  </div>
</template>

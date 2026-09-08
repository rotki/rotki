<script setup lang="ts">
import type { RemediationTimelineItem } from '@/modules/history/data-issues/types';
import DataIssueDecodingReview from '@/modules/history/data-issues/components/DataIssueDecodingReview.vue';
import { humanizeStrategy } from '@/modules/history/data-issues/transforms';
import DateDisplay from '@/modules/shell/components/display/DateDisplay.vue';

const { items, asset } = defineProps<{
  items: RemediationTimelineItem[];
  asset?: string | null;
}>();

const emit = defineEmits<{
  navigate: [groupIdentifier: string];
}>();

const { t } = useI18n({ useScope: 'global' });

function isFailure(item: RemediationTimelineItem): boolean {
  return item.success === false || item.result === 'redecoding_failed';
}

function getResultText(item: RemediationTimelineItem): string | undefined {
  switch (item.result) {
    case 'redecoding_failed':
      return t('data_issues.detail.redecoding_failed');
    case 'redecoding_would_change_balance':
      return t('data_issues.detail.redecoding_would_change_balance');
    case 'redecoding_would_not_change_balance':
      return t('data_issues.detail.redecoding_would_not_change_balance');
    default:
      return undefined;
  }
}
</script>

<template>
  <div data-testid="data-issue-timeline">
    <div
      v-if="items.length === 0"
      class="text-body-2 text-rui-text-secondary"
    >
      {{ t('data_issues.detail.no_attempts') }}
    </div>
    <ol
      v-else
      class="flex flex-col gap-3"
    >
      <li
        v-for="(item, index) in items"
        :key="index"
        class="flex items-start gap-3"
      >
        <RuiIcon
          class="mt-0.5"
          size="18"
          :name="isFailure(item) ? 'lu-circle-x' : item.success ? 'lu-circle-check' : 'lu-circle-dot'"
          :color="isFailure(item) ? 'error' : item.success ? 'success' : 'secondary'"
        />
        <div class="flex flex-col">
          <span class="text-body-2 font-medium">
            {{ item.strategy === 'redecode_customized_transactions' ? t('data_issues.detail.checked_customizations') : humanizeStrategy(item.strategy) }}
          </span>
          <span
            v-if="getResultText(item)"
            class="text-body-2 text-rui-text-secondary"
          >
            {{ getResultText(item) }}
          </span>
          <span
            v-if="item.customizedTransactionCount !== undefined && item.changedTransactionCount !== undefined"
            class="text-body-2 mt-2"
            data-testid="data-issue-timeline-counts"
          >
            {{ t('data_issues.detail.comparison_counts', { total: item.customizedTransactionCount, changed: item.changedTransactionCount }) }}
          </span>
          <DataIssueDecodingReview
            v-if="item.transactions?.length && asset"
            :transactions="item.transactions"
            :asset="asset"
            :timestamp="item.timestamp"
            @navigate="emit('navigate', $event)"
          />
          <span
            v-else-if="item.result === 'redecoding_would_change_balance'"
            class="text-body-2 text-rui-text-secondary mt-2"
          >
            {{ t('data_issues.detail.comparison_unavailable') }}
          </span>
          <span
            v-if="item.attribution"
            class="text-caption text-rui-text-secondary"
          >
            {{ item.attribution }}
          </span>
          <DateDisplay
            v-if="item.timestamp"
            class="text-caption text-rui-text-secondary"
            :timestamp="item.timestamp"
          />
        </div>
      </li>
    </ol>
  </div>
</template>

<script setup lang="ts">
import type { RemediationTimelineItem } from '@/modules/history/data-issues/types';
import { humanizeStrategy } from '@/modules/history/data-issues/transforms';
import DateDisplay from '@/modules/shell/components/display/DateDisplay.vue';

const { items } = defineProps<{
  items: RemediationTimelineItem[];
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
          <span class="text-body-2 font-medium">{{ humanizeStrategy(item.strategy) }}</span>
          <span
            v-if="getResultText(item)"
            class="text-body-2 text-rui-text-secondary"
          >
            {{ getResultText(item) }}
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

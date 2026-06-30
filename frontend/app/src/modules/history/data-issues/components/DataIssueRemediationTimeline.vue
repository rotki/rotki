<script setup lang="ts">
import type { RemediationTimelineItem } from '@/modules/history/data-issues/types';
import { humanizeStrategy } from '@/modules/history/data-issues/transforms';
import DateDisplay from '@/modules/shell/components/display/DateDisplay.vue';

const { items } = defineProps<{
  items: RemediationTimelineItem[];
}>();

const { t } = useI18n({ useScope: 'global' });
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
          :name="item.success === false ? 'lu-circle-x' : item.success ? 'lu-circle-check' : 'lu-circle-dot'"
          :color="item.success === false ? 'error' : item.success ? 'success' : 'secondary'"
        />
        <div class="flex flex-col">
          <span class="text-body-2 font-medium">{{ humanizeStrategy(item.strategy) }}</span>
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

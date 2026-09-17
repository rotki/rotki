<script setup lang="ts">
import type { Activity } from '@/modules/task-center/core/types';
import DateDisplay from '@/modules/shell/components/display/DateDisplay.vue';
import DockCacheList from '@/modules/task-center/components/DockCacheList.vue';
import { useDockActivityDetail } from '@/modules/task-center/use-dock-activity-detail';

const { activity } = defineProps<{
  activity: Activity;
}>();

const { t } = useI18n({ useScope: 'global' });

const detail = useDockActivityDetail(() => activity);
</script>

<template>
  <div
    v-if="detail?.type === 'query' && (detail.step || detail.period)"
    class="flex flex-wrap items-center gap-x-1 text-xs leading-4 text-rui-text-secondary"
    data-testid="dock-activity-detail"
  >
    <span v-if="detail.step">{{ detail.step }}</span>
    <template v-if="detail.period">
      <span
        v-if="detail.step"
        class="before:content-['·']"
        aria-hidden="true"
      />
      <DateDisplay
        v-if="detail.period.from !== undefined"
        :timestamp="detail.period.from"
        no-time
        hide-tooltip
      />
      <span v-else>{{ t('task_dock.detail.beginning') }}</span>
      <RuiIcon
        name="lu-arrow-right"
        size="12"
      />
      <DateDisplay
        :timestamp="detail.period.to"
        no-time
        hide-tooltip
      />
    </template>
  </div>
  <DockCacheList
    v-else-if="detail?.type === 'caches'"
    :filling="detail.filling"
    :filled="detail.filled"
    :stopped="detail.stopped"
    data-testid="dock-activity-detail"
  />
</template>

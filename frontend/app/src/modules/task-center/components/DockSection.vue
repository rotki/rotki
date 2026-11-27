<script setup lang="ts">
import type { Activity, ActivityId } from '@/modules/task-center/core/types';
import type { DockSection } from '@/modules/task-center/use-dock-panel';
import { RuiIcon } from '@rotki/ui-library';
import { get } from '@vueuse/shared';
import { computed, provide, ref } from 'vue';
import { useI18n } from 'vue-i18n';
import DockJobNode from '@/modules/task-center/components/DockJobNode.vue';
import { formatElapsed } from '@/modules/task-center/core/elapsed';
import { DockKindHeadingKey } from '@/modules/task-center/dock-section';

const { children, dismissible = false, now, section } = defineProps<{
  section: DockSection;
  /** The whole tree, passed down to each job. */
  children: ReadonlyMap<ActivityId, Activity[]>;
  now: number;
  /** Offers each job's row a dismiss control. */
  dismissible?: boolean;
}>();

const emit = defineEmits<{
  cancel: [activity: Activity];
  dismiss: [activity: Activity];
  retry: [activity: Activity];
}>();

const { t } = useI18n({ useScope: 'global' });

/** A section shorter than a second reports no time, as a row does. */
const MIN_SHOWN_SPAN = 1000;

provide(DockKindHeadingKey, () => section.kindHeading === true);

/** Whether the user opened a folded section; a section that stops being foldable shows its rows regardless. */
const opened = ref<boolean>(false);

const showRows = computed<boolean>(() => !section.folded || get(opened));

/** How many jobs the heading names; the finished group's own title already counts them. */
const jobCount = computed<string | undefined>(() => (section.kindHeading
  ? t('task_dock.panel.section_jobs', { count: section.roots.length }, section.roots.length)
  : undefined));

/**
 * The wall time the folded jobs took between them, from the first start to the last finish. Jobs
 * run side by side, so adding their durations up would overstate it.
 */
const span = computed<string | undefined>(() => {
  const starts = section.roots.flatMap(root => (root.startedAt === undefined ? [] : [root.startedAt]));
  const ends = section.roots.flatMap(root => (root.settledAt === undefined ? [] : [root.settledAt]));
  if (starts.length === 0 || ends.length !== section.roots.length)
    return undefined;
  const took = Math.max(...ends) - Math.min(...starts);
  return took >= MIN_SHOWN_SPAN ? formatElapsed(took) : undefined;
});

const toggleLabel = computed<string>(() => (get(opened) ? t('pending_task.collapse') : t('pending_task.expand')));
</script>

<template>
  <div
    class="flex flex-col"
    data-testid="dock-section"
  >
    <button
      v-if="section.folded && section.title"
      type="button"
      class="flex items-center gap-1.5 pt-2 pb-1 pr-15 text-xs leading-4 text-rui-text-secondary text-left hover:text-rui-text focus-visible:outline-2 focus-visible:outline-rui-primary rounded-sm"
      :aria-expanded="showRows"
      :aria-label="`${section.title}, ${toggleLabel}`"
      data-testid="dock-section-toggle"
      @click="opened = !opened"
    >
      <RuiIcon
        :name="showRows ? 'lu-chevron-down' : 'lu-chevron-right'"
        size="14"
      />
      <span
        class="font-medium uppercase tracking-wide truncate"
        data-testid="dock-section-title"
      >
        {{ section.title }}
      </span>
      <span
        v-if="jobCount"
        class="shrink-0 tabular-nums before:content-['·'] before:mr-1.5"
        data-testid="dock-section-count"
      >
        {{ jobCount }}
      </span>
      <span
        v-if="span"
        class="ml-auto shrink-0 tabular-nums"
        data-testid="dock-section-span"
      >
        {{ span }}
      </span>
    </button>
    <div
      v-else-if="section.title"
      class="pt-2 pb-1 text-xs font-medium uppercase tracking-wide text-rui-text-secondary"
      data-testid="dock-section-title"
    >
      {{ section.title }}
    </div>
    <div
      v-if="showRows"
      class="flex flex-col divide-y divide-rui-grey-200 dark:divide-rui-grey-800"
    >
      <DockJobNode
        v-for="root in section.roots"
        :key="root.id"
        :activity="root"
        :children="children"
        :now="now"
        :dismissible="dismissible"
        @cancel="emit('cancel', $event)"
        @dismiss="emit('dismiss', $event)"
        @retry="emit('retry', $event)"
      />
    </div>
  </div>
</template>

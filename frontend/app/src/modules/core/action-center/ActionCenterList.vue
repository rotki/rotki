<script setup lang="ts" generic="TTarget extends { kind: string }">
import type { ActionCenterSection, ActionItem } from '@/modules/core/action-center/types';
import ActionCenterGroup from '@/modules/core/action-center/ActionCenterGroup.vue';

/** ids of the sections the user folded */
const folded = defineModel<string[]>('folded', { default: () => [] });

const {
  checking = false,
  cleared,
  count,
  newIds = [],
  previousCounts = {},
  refreshing = false,
  sections,
} = defineProps<{
  /** ids of the rows that appeared or grew since the user last looked, marked as new */
  newIds?: string[];
  /** the count each row that went down, or cleared, had when the user last looked, by row id */
  previousCounts?: Record<string, number>;
  /** the rows worth showing, grouped under headings in the order they should appear */
  sections: ActionCenterSection<TTarget>[];
  /** categories with nothing pending, rendered as the checked strip */
  cleared: ActionItem<TTarget>[];
  /** how many categories are actually asking for something (drives the subtitle) */
  count: number;
  /** no scan has finished yet, so an empty list reads as "checking", not as "all clear" */
  checking?: boolean;
  /** a re-scan is under way: shown as a thin bar over rows that stay in place */
  refreshing?: boolean;
}>();

const emit = defineEmits<{
  open: [target: TTarget];
  refresh: [];
}>();

const { t } = useI18n({ useScope: 'global' });

const title = computed<string>(() => {
  if (count > 0)
    return t('action_center.title');
  return checking ? t('action_center.title_checking') : t('action_center.title_clear');
});

const subtitle = computed<string>(() => {
  if (count > 0)
    return t('action_center.subtitle', { count }, count);
  if (checking)
    return t('action_center.subtitle_checking');
  return t('action_center.subtitle_clear');
});

const clearedToggled = ref<boolean>();

function clearedSinceLastVisit(item: ActionItem<TTarget>): boolean {
  return (previousCounts[item.id] ?? 0) > 0;
}

/** The checked categories, the ones cleared since the user last looked first. */
const clearedRows = computed<ActionItem<TTarget>[]>(() => [
  ...cleared.filter(clearedSinceLastVisit),
  ...cleared.filter(item => !clearedSinceLastVisit(item)),
]);

const anyClearedSinceLastVisit = computed<boolean>(() => cleared.some(clearedSinceLastVisit));

/**
 * Whether the checked categories are listed, not just counted.
 *
 * @remarks
 * With nothing asking for attention the list is the evidence that everything was checked, so it
 * opens, and so it does when something cleared since the user last looked; otherwise, next to rows
 * that need something, it is background and stays folded. The default follows these until the user
 * toggles it.
 */
const clearedExpanded = computed<boolean>(() => get(clearedToggled) ?? (count === 0 || get(anyClearedSinceLastVisit)));

function toggleCleared(): void {
  set(clearedToggled, !get(clearedExpanded));
}

function setFolded(id: string, fold: boolean): void {
  const others = get(folded).filter(foldedId => foldedId !== id);
  set(folded, fold ? [...others, id] : others);
}
</script>

<template>
  <div
    class="relative flex flex-col max-h-[calc(100vh-6rem)]"
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
        @click="emit('refresh')"
      >
        <template #prepend>
          <RuiIcon
            name="lu-refresh-ccw"
            size="16"
          />
        </template>
        {{ t('action_center.rescan') }}
      </RuiButton>
    </div>

    <div
      class="flex-1 min-h-0 overflow-y-auto"
      data-testid="actions-center-body"
    >
      <ActionCenterGroup
        v-for="section in sections"
        :key="section.id"
        :section="section"
        :new-ids="newIds"
        :previous-counts="previousCounts"
        :folded="folded.includes(section.id)"
        @update:folded="setFolded(section.id, $event)"
        @open="emit('open', $event)"
      />

      <div
        v-if="!checking && cleared.length > 0"
        class="px-4 py-3 bg-rui-grey-50 dark:bg-rui-grey-900"
        data-testid="actions-center-cleared"
      >
        <button
          type="button"
          class="flex items-center gap-1.5 text-caption text-rui-text-secondary hover:text-rui-text"
          :aria-expanded="clearedExpanded"
          data-testid="actions-center-cleared-toggle"
          @click="toggleCleared()"
        >
          <RuiIcon
            name="lu-circle-check"
            size="14"
            color="success"
          />
          {{ t('action_center.checks_passed', { count: cleared.length }, cleared.length) }}
          <RuiIcon
            :name="clearedExpanded ? 'lu-chevron-up' : 'lu-chevron-down'"
            size="14"
          />
        </button>
        <div
          v-if="clearedExpanded"
          class="flex flex-wrap items-center gap-x-4 gap-y-1 pt-2 pl-5"
        >
          <button
            v-for="item in clearedRows"
            :key="item.id"
            type="button"
            class="text-caption text-rui-text-secondary hover:text-rui-text hover:underline"
            data-testid="actions-center-cleared-row"
            :data-key="item.id"
            @click="emit('open', item.checkTarget)"
          >
            {{ item.title }}
            <span
              v-if="clearedSinceLastVisit(item)"
              class="ml-1 text-rui-success"
              data-testid="actions-center-cleared-since"
            >
              {{ t('action_center.cleared_since_last_visit') }}
            </span>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

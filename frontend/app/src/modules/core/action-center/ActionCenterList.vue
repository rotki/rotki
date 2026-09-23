<script setup lang="ts" generic="TTarget extends { kind: string }">
import type { ActionCenterSection, ActionItem } from '@/modules/core/action-center/types';
import ActionCenterRow from '@/modules/core/action-center/ActionCenterRow.vue';

const {
  checking = false,
  cleared,
  count,
  newIds = [],
  refreshing = false,
  sections,
} = defineProps<{
  /** ids of the rows that appeared or grew since the user last looked, marked as new */
  newIds?: string[];
  /** the rows worth showing, grouped under headings in the order they should appear */
  sections: ActionCenterSection<TTarget>[];
  /** categories with nothing pending, rendered as the checked strip */
  cleared: ActionItem<TTarget>[];
  /** how many categories are actually asking for something (drives the subtitle) */
  count: number;
  checking?: boolean;
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

/**
 * Whether the checked categories are listed, not just counted.
 *
 * @remarks
 * With nothing asking for attention the list is the evidence that everything was checked, so it
 * opens; next to rows that need something it is background, so it stays folded. The default follows
 * the count until the user toggles it.
 */
const clearedExpanded = computed<boolean>(() => get(clearedToggled) ?? count === 0);

function toggleCleared(): void {
  set(clearedToggled, !get(clearedExpanded));
}
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

    <section
      v-for="section in sections"
      :key="section.id"
      data-testid="actions-center-section"
      :data-key="section.id"
    >
      <h6 class="px-4 pt-3 text-caption font-medium uppercase text-rui-text-secondary">
        {{ section.title }}
      </h6>
      <div class="px-4 divide-y divide-rui-grey-200 dark:divide-rui-grey-800">
        <ActionCenterRow
          v-for="item in section.items"
          :key="item.id"
          :item="item"
          :is-new="newIds.includes(item.id)"
          @action="emit('open', $event.target)"
          @option="emit('open', $event)"
        />
      </div>
    </section>

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
          v-for="item in cleared"
          :key="item.id"
          type="button"
          class="text-caption text-rui-text-secondary hover:text-rui-text hover:underline"
          data-testid="actions-center-cleared-row"
          :data-key="item.id"
          @click="emit('open', item.checkTarget)"
        >
          {{ item.title }}
        </button>
      </div>
    </div>
  </div>
</template>

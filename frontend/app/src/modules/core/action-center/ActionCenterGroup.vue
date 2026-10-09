<script setup lang="ts" generic="TTarget extends { kind: string }">
import ActionCenterRow from '@/modules/core/action-center/ActionCenterRow.vue';
import { type GroupSummary, summarizeGroup } from '@/modules/core/action-center/group-summary';
import { type ActionCenterSection, URGENCY_COLORS } from '@/modules/core/action-center/types';

const folded = defineModel<boolean>('folded', { default: false });

const { newIds = [], previousCounts = {}, section } = defineProps<{
  section: ActionCenterSection<TTarget>;
  /** ids of the rows that appeared or grew since the user last looked, marked as new */
  newIds?: string[];
  /** the count each row that went down had when the user last looked, by row id */
  previousCounts?: Record<string, number>;
}>();

const emit = defineEmits<{
  open: [target: TTarget];
}>();

const { t } = useI18n({ useScope: 'global' });

const summary = computed<GroupSummary>(() => summarizeGroup(section.items, newIds));

const rowsId = computed<string>(() => `actions-center-group-rows-${section.id}`);

function toggle(): void {
  set(folded, !get(folded));
}
</script>

<template>
  <section
    class="border-t border-default first-of-type:border-t-0"
    :class="{ 'pb-3': folded }"
    data-testid="actions-center-section"
    :data-key="section.id"
  >
    <button
      type="button"
      class="flex w-full items-center gap-2 px-4 pt-3 text-left text-rui-text-secondary hover:text-rui-text"
      :aria-expanded="!folded"
      :aria-controls="rowsId"
      data-testid="actions-center-section-toggle"
      @click="toggle()"
    >
      <span class="text-caption font-medium uppercase tracking-wide">
        {{ section.title }}
      </span>
      <template v-if="folded">
        <RuiChip
          size="sm"
          :color="summary.urgency ? URGENCY_COLORS[summary.urgency] : undefined"
          variant="outlined"
          class="h-5! px-1.5! tabular-nums"
          data-testid="actions-center-section-count"
        >
          {{ summary.count }}
        </RuiChip>
        <span
          v-if="summary.hasNew"
          class="text-caption font-medium text-rui-primary"
          data-testid="actions-center-section-new"
        >
          {{ t('action_center.new') }}
        </span>
      </template>
      <RuiIcon
        :name="folded ? 'lu-chevron-down' : 'lu-chevron-up'"
        size="14"
        class="ml-auto"
      />
    </button>
    <div
      v-if="!folded"
      :id="rowsId"
      class="px-4 divide-y divide-rui-grey-200 dark:divide-rui-grey-800"
    >
      <ActionCenterRow
        v-for="item in section.items"
        :key="item.id"
        :item="item"
        :is-new="newIds.includes(item.id)"
        :previous-count="previousCounts[item.id]"
        @action="emit('open', $event.target)"
        @option="emit('open', $event)"
      />
    </div>
  </section>
</template>

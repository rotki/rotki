<script setup lang="ts" generic="TTarget extends { kind: string }">
import type { ActionItem } from '@/modules/core/action-center/types';
import ActionCenterRow from '@/modules/core/action-center/ActionCenterRow.vue';

const {
  checking = false,
  checkingHint,
  cleared,
  clearHint,
  count,
  items,
  refreshing = false,
} = defineProps<{
  /** the rows worth showing, in the order they should appear */
  items: ActionItem<TTarget>[];
  /** categories with nothing pending, rendered as the checked strip */
  cleared: ActionItem<TTarget>[];
  /** how many categories are actually asking for something (drives the subtitle) */
  count: number;
  checking?: boolean;
  refreshing?: boolean;
  /** what the center is waiting for, when the domain can say something better than the default */
  checkingHint?: string;
  /** what came back clean, when the domain can say something better than the default */
  clearHint?: string;
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
    return checkingHint ?? t('action_center.subtitle_checking');
  return clearHint ?? t('action_center.subtitle_clear');
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
      v-if="items.length > 0"
      class="px-4 divide-y divide-rui-grey-200 dark:divide-rui-grey-800"
    >
      <ActionCenterRow
        v-for="item in items"
        :key="item.id"
        :item="item"
        @action="emit('open', $event.target)"
      />
    </div>

    <div
      v-if="!checking && cleared.length > 0"
      class="flex flex-wrap items-center gap-x-4 gap-y-1 px-4 py-3 bg-rui-grey-50 dark:bg-rui-grey-900"
      data-testid="actions-center-cleared"
    >
      <span class="text-caption text-rui-text-disabled">
        {{ t('action_center.cleared') }}
      </span>
      <button
        v-for="item in cleared"
        :key="item.id"
        type="button"
        class="flex items-center gap-1.5 text-caption text-rui-text-secondary hover:text-rui-text hover:underline"
        data-testid="actions-center-cleared-row"
        :data-key="item.id"
        @click="emit('open', item.checkTarget)"
      >
        <RuiIcon
          name="lu-circle-check"
          size="14"
          color="success"
        />
        {{ item.title }}
      </button>
    </div>
  </div>
</template>

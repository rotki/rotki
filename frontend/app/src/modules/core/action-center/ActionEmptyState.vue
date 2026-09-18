<script setup lang="ts">
import type { ActionItem } from '@/modules/core/action-center/types';
import ActionCenterRowAction from '@/modules/core/action-center/ActionCenterRowAction.vue';
import { useOpenActionTarget } from '@/modules/core/action-center/use-open-action-target';

const { item } = defineProps<{
  /**
   * The action center row that explains why the page is empty.
   *
   * @remarks
   * Only its description and action are shown, as the page's own empty state: the title and count
   * belong to the center's list and read as a stray widget on an empty page. The row stays the one
   * source of the wording and the ways to fix it.
   */
  item: ActionItem;
}>();

const { openTarget } = useOpenActionTarget();

/** Out of the center, there is no panel to close before following a target. */
function stayPut(): void {}
</script>

<template>
  <div
    class="flex gap-3"
    data-testid="action-empty-state"
    :data-key="item.id"
  >
    <div class="shrink-0 self-start rounded-full p-2 bg-rui-primary/10 text-rui-primary">
      <RuiIcon
        :name="item.icon"
        size="18"
      />
    </div>
    <div class="flex flex-col items-start gap-3 pt-1">
      <p class="text-sm text-rui-text-secondary">
        {{ item.description }}
      </p>
      <ActionCenterRowAction
        :item="item"
        color="primary"
        @action="openTarget($event.target, stayPut)"
        @option="openTarget($event, stayPut)"
      />
    </div>
  </div>
</template>

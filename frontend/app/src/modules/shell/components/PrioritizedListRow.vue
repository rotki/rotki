<script setup lang="ts">
import type { PrioritizedListItemData } from '@/modules/settings/types/prioritized-list-data';
import type { PrioritizedListId } from '@/modules/settings/types/prioritized-list-id';
import PrioritizedListEntry from '@/modules/shell/components/PrioritizedListEntry.vue';

interface RowItem {
  identifier: PrioritizedListId;
  index: number;
  data: PrioritizedListItemData<PrioritizedListId>;
  first: boolean;
  last: boolean;
}

const { item, dense = false, disableDelete = false, deleteLabel } = defineProps<{
  item: RowItem;
  dense?: boolean;
  disableDelete?: boolean;
  deleteLabel: string;
}>();

const emit = defineEmits<{
  move: [down: boolean];
  remove: [];
}>();

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <tr class="group">
    <td
      class="text-center tabular-nums text-rui-text-secondary"
      :class="dense ? 'py-1.5' : 'py-2.5'"
    >
      {{ item.index + 1 }}
    </td>
    <td
      class="pl-0"
      :class="dense ? 'py-1.5' : 'py-2.5'"
    >
      <PrioritizedListEntry
        :data="item.data"
        :size="dense ? '20px' : '24px'"
      />
    </td>
    <td
      class="w-px pl-0 pr-2"
      :class="dense ? 'py-1.5' : 'py-2.5'"
    >
      <div class="flex items-center justify-end gap-0.5 transition-opacity [tr:not(:hover)_&:not(:focus-within)]:opacity-0 motion-reduce:transition-none">
        <RuiButton
          :id="`move-up-${item.identifier}`"
          variant="text"
          icon
          size="sm"
          :disabled="item.first"
          :aria-label="t('prioritized_list.item.move_up')"
          @click="emit('move', false)"
        >
          <RuiIcon
            name="lu-arrow-up"
            size="16"
          />
        </RuiButton>
        <RuiButton
          :id="`move-down-${item.identifier}`"
          variant="text"
          icon
          size="sm"
          :disabled="item.last"
          :aria-label="t('prioritized_list.item.move_down')"
          @click="emit('move', true)"
        >
          <RuiIcon
            name="lu-arrow-down"
            size="16"
          />
        </RuiButton>
        <RuiTooltip
          v-if="!disableDelete"
          :options="{ placement: 'top' }"
          :open-delay="400"
        >
          <template #activator>
            <RuiButton
              :id="`delete-${item.identifier}`"
              variant="text"
              icon
              size="sm"
              :aria-label="deleteLabel"
              @click="emit('remove')"
            >
              <RuiIcon
                name="lu-x"
                size="16"
              />
            </RuiButton>
          </template>
          {{ deleteLabel }}
        </RuiTooltip>
      </div>
    </td>
  </tr>
</template>

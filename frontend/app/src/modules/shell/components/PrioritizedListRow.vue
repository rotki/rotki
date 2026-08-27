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
</script>

<template>
  <tr class="odd:bg-rui-grey-50 odd:dark:bg-rui-grey-900 group">
    <td class="!pr-0 !pl-2">
      <div class="flex flex-col gap-1 transition-all opacity-0 invisible group-hover:opacity-100 group-hover:visible">
        <RuiButton
          :id="`move-up-${item.identifier}`"
          size="sm"
          class="!px-1"
          :class="{ '!py-0.5': dense }"
          :disabled="item.first"
          @click="emit('move', false)"
        >
          <RuiIcon
            name="lu-arrow-up"
            size="16"
          />
        </RuiButton>
        <RuiButton
          :id="`move-down-${item.identifier}`"
          size="sm"
          class="!px-1"
          :class="{ '!py-0.5': dense }"
          :disabled="item.last"
          @click="emit('move', true)"
        >
          <RuiIcon
            name="lu-arrow-down"
            size="16"
          />
        </RuiButton>
      </div>
    </td>
    <td class="text-center px-0">
      {{ item.index + 1 }}
    </td>
    <td>
      <PrioritizedListEntry
        :data="item.data"
        size="28px"
      />
    </td>
    <td class="text-end !pl-0">
      <RuiTooltip
        v-if="!disableDelete"
        :options="{ placement: 'top' }"
        :open-delay="400"
      >
        <template #activator>
          <RuiButton
            :id="`delete-${item.identifier}`"
            class="transition-all opacity-0 invisible group-hover:opacity-100 group-hover:visible"
            icon
            :class="{ '!p-2': dense }"
            variant="text"
            @click="emit('remove')"
          >
            <RuiIcon
              name="lu-x"
              :size="dense ? 16 : 20"
            />
          </RuiButton>
        </template>
        <span>
          {{ deleteLabel }}
        </span>
      </RuiTooltip>
    </td>
  </tr>
</template>

<script setup lang="ts">
import type { Suggestion } from '@/types/filtering';
import SuggestedItem from '@/components/table-filter/SuggestedItem.vue';

defineOptions({
  inheritAttrs: false,
});

const expandedGroupKey = defineModel<string | undefined>('expandedGroupKey');

const props = defineProps<{
  item: Suggestion;
  chipAttrs: Record<string, unknown>;
  displayType: 'normal' | 'grouped' | 'hidden';
  editMode: boolean;
  overflowCount: number;
  groupedItems: Suggestion[];
}>();

const emit = defineEmits<{
  'click-item': [item: Suggestion];
  'cancel-edit': [skipClearSearch?: boolean];
  'update:search': [value: string];
  'toggle-group-menu': [key: string];
  'remove-all-items': [key: string];
  'remove-grouped-item': [item: Suggestion];
}>();

const { item } = toRefs(props);

const isMenuOpen = computed<boolean>(() => get(expandedGroupKey) === get(item).key);

function onMenuUpdate(value: boolean): void {
  set(expandedGroupKey, value ? get(item).key : undefined);
}
</script>

<template>
  <!-- Normal chip for non-grouped items -->
  <RuiChip
    v-if="displayType === 'normal'"
    tile
    size="sm"
    class="font-medium !py-0"
    clickable
    closeable
    v-bind="chipAttrs"
    @click="emit('click-item', item)"
  >
    <SuggestedItem
      chip
      :edit-mode="editMode"
      :suggestion="item"
      @cancel-edit="emit('cancel-edit', $event)"
      @update:search="emit('update:search', $event)"
    />
  </RuiChip>

  <!-- Grouped chip with menu for grouped items (only first item) -->
  <RuiMenu
    v-else-if="displayType === 'grouped'"
    :model-value="isMenuOpen"
    menu-class="max-w-[20rem] !max-h-[50vh] overflow-auto"
    @update:model-value="onMenuUpdate($event)"
  >
    <template #activator="{ attrs }">
      <RuiChip
        tile
        size="sm"
        class="font-medium !py-0"
        content-class="flex items-center gap-1"
        clickable
        v-bind="attrs"
        @click.stop="emit('click-item', item)"
      >
        <SuggestedItem
          chip
          :edit-mode="editMode"
          :suggestion="item"
          @cancel-edit="emit('cancel-edit', $event)"
          @update:search="emit('update:search', $event)"
        />
        <span
          class="text-xs px-1.5 py-0.5 rounded bg-rui-primary text-white cursor-pointer"
          @click.stop="emit('toggle-group-menu', item.key)"
        >
          {{ overflowCount }}+
        </span>
        <RuiButton
          variant="text"
          type="button"
          icon
          size="sm"
          class="-mr-1 !p-0.5 opacity-50 hover:opacity-80 transition-opacity"
          @click.stop="emit('remove-all-items', item.key)"
        >
          <RuiIcon
            name="lu-circle-x"
            size="16"
          />
        </RuiButton>
      </RuiChip>
    </template>
    <div class="flex flex-wrap gap-1 p-2">
      <RuiChip
        v-for="(groupedItem, index) in groupedItems"
        :key="index"
        tile
        size="sm"
        class="font-medium !py-0"
        closeable
        @click:close="emit('remove-grouped-item', groupedItem)"
      >
        <SuggestedItem
          chip
          :suggestion="groupedItem"
        />
      </RuiChip>
    </div>
  </RuiMenu>

  <!-- Hidden items (other items in grouped keys) -->
  <div
    v-else
    data-testid="hidden-selection-chip"
    class="hidden"
  />
</template>

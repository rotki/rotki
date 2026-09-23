<script setup lang="ts">
import { isEqual } from 'es-toolkit';
import { useLocations } from '@/modules/core/common/use-locations';
import { type LocationOption, locationOptions } from '@/modules/locations/location-options';
import { useLocationTreeStore } from '@/modules/locations/use-location-tree-store';
import LocationIcon from '@/modules/shell/components/display/LocationIcon.vue';

defineOptions({
  inheritAttrs: false,
});

const model = defineModel<string>({ default: '', required: true });

const { dense, excludes = [], items = [] } = defineProps<{
  items?: readonly string[];
  excludes?: readonly string[];
  dense?: boolean;
}>();

/**
 * The height of an option: its fixed 40px content plus the vertical padding of the menu's list
 * button, 12px a side or 4px when dense.
 *
 * @remarks
 * The menu is a virtual list that places every option at a multiple of this height, so each
 * option has to render exactly this tall, with or without a path line.
 */
const ITEM_HEIGHT = 64;
const DENSE_ITEM_HEIGHT = 48;

const { tradeLocations } = useLocations();
const treeStore = useLocationTreeStore();
const { assignableNodes, nodes } = storeToRefs(treeStore);

const locations = computed<LocationOption[]>(() => locationOptions({
  assignable: get(nodes).length > 0 ? new Set(get(assignableNodes).map(node => node.identifier)) : undefined,
  current: get(model),
  excludes,
  items,
  locations: get(tradeLocations),
  pathOf: treeStore.pathOf,
}));

watch([locations, model], ([locations, value], [prevLocations, prevValue]) => {
  if (isEqual(locations, prevLocations) && value === prevValue)
    return;

  if (!locations.some(item => item.identifier === value))
    set(model, '');
});
</script>

<template>
  <RuiAutoComplete
    v-model="model"
    variant="outlined"
    data-testid="location-input"
    :options="locations"
    key-attr="identifier"
    text-attr="label"
    :item-height="dense ? DENSE_ITEM_HEIGHT : ITEM_HEIGHT"
    :dense="dense"
    auto-select-first
    v-bind="$attrs"
  >
    <template #item="{ disabled, item }">
      <div
        :id="`balance-location__${item.identifier}`"
        class="flex items-center gap-2 h-10 min-w-0"
        :class="{ 'opacity-40': disabled }"
      >
        <LocationIcon
          class="shrink-0"
          icon
          :item="item.identifier"
        />
        <div class="flex flex-col min-w-0 leading-5">
          <span class="truncate text-rui-text-secondary">{{ item.name }}</span>
          <span
            v-if="item.parentPath"
            class="truncate text-caption text-rui-text-secondary"
            data-testid="location-option-path"
          >
            {{ item.parentPath }}
          </span>
        </div>
      </div>
    </template>
    <template #selection="{ item }">
      <div
        class="flex items-center gap-2 pr-2 min-w-0"
        data-testid="location-selection"
      >
        <LocationIcon
          class="shrink-0"
          icon
          :item="item.identifier"
        />
        <span class="truncate text-rui-text-secondary">{{ treeStore.distinctNameOf(item.identifier) ?? item.name }}</span>
      </div>
    </template>
  </RuiAutoComplete>
</template>

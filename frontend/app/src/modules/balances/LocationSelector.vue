<script setup lang="ts">
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
const { assignableIdentifiers } = storeToRefs(treeStore);

/**
 * The current value when new data can no longer go there, so that an old record still shows it,
 * and empty otherwise.
 *
 * @remarks
 * Picking between assignable locations leaves this empty, so the options are not rebuilt on
 * every pick.
 */
const keptValue = computed<string>(() => {
  const value = get(model);
  const assignable = get(assignableIdentifiers);
  return assignable === undefined || assignable.has(value) ? '' : value;
});

const locations = computed<LocationOption[]>(() => locationOptions({
  assignable: get(assignableIdentifiers),
  current: get(keptValue),
  excludes,
  items,
  locations: get(tradeLocations),
  pathOf: treeStore.pathOf,
}));

/**
 * Clears a value the selector does not offer, such as one its `items` or `excludes` leave out.
 *
 * @remarks
 * A value without display data yet is kept: the location details and the tree load in the
 * background, and clearing a record's location before they arrive would save it elsewhere.
 */
function clearUnoffered(locations: LocationOption[], value: string): void {
  if (!value || locations.some(item => item.identifier === value))
    return;
  if (!get(tradeLocations).some(location => location.identifier === value))
    return;
  set(model, '');
}

watch([locations, model], ([locations, value]) => clearUnoffered(locations, value));
</script>

<template>
  <RuiAutoComplete
    v-model="model"
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

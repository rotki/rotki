<script setup lang="ts">
import type { RuiAutoComplete } from '@rotki/ui-library';
import type { ForwardedProps } from '@/modules/core/common/forwarded-props';
import type { TradeLocationData } from '@/modules/core/common/location';
import { useLocations } from '@/modules/core/common/use-locations';
import { type LocationOption, locationOptions } from '@/modules/locations/location-options';
import { useLocationTreeStore } from '@/modules/locations/use-location-tree-store';
import LocationIcon from '@/modules/shell/components/display/LocationIcon.vue';

interface Props {
  items?: readonly string[];
  excludes?: readonly string[];
  dense?: boolean;
}

defineOptions({
  inheritAttrs: false,
});

const model = defineModel<string>({ default: '', required: true });

const { dense, excludes = [], items = [] } = defineProps<Props & /* @vue-ignore */ ForwardedProps<typeof RuiAutoComplete<string, LocationOption>, Props>>();

/**
 * The height of an option when at least one option in the list shows a path line: its fixed 40px
 * content plus the vertical padding of the menu's list button, 12px a side or 8px when dense (the
 * small button size).
 *
 * @remarks
 * The menu is a virtual list that places every option at a multiple of this height, so each
 * option has to render exactly this tall, with or without a path line of its own.
 */
const PATH_ITEM_HEIGHT = 64;
const DENSE_PATH_ITEM_HEIGHT = 56;

/**
 * The height of an option when no option in the list has a path: its fixed 28px content, a
 * single line, plus the same padding.
 */
const ITEM_HEIGHT = 52;
const DENSE_ITEM_HEIGHT = 44;

const { getLocationData, tradeLocations } = useLocations();
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

/**
 * The locations named the way the rest of the app names them, as the location icons do: a chain by
 * its name in the chain list, such as `BNB Smart Chain` for `binance sc`.
 */
const displayLocations = computed<TradeLocationData[]>(() => get(tradeLocations).map(location => ({
  ...location,
  name: getLocationData(location.identifier)?.name ?? location.name,
})));

const locations = computed<LocationOption[]>(() => locationOptions({
  assignable: get(assignableIdentifiers),
  current: get(keptValue),
  excludes,
  items,
  locations: get(displayLocations),
  pathOf: treeStore.pathOf,
}));

/** Whether any option shows a path line, which makes every row tall enough to hold one. */
const hasPaths = computed<boolean>(() => get(locations).some(location => location.parentPath !== ''));

/**
 * The row height the menu lays its options out at.
 *
 * @remarks
 * The autocomplete reads its item height once, when it is built, so the menu is keyed on this
 * value: a path line that appears later, as the tree loads or a location is added, rebuilds it.
 */
const itemHeight = computed<number>(() => {
  if (get(hasPaths))
    return dense ? DENSE_PATH_ITEM_HEIGHT : PATH_ITEM_HEIGHT;
  return dense ? DENSE_ITEM_HEIGHT : ITEM_HEIGHT;
});

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
    :key="itemHeight"
    v-model="model"
    data-testid="location-input"
    :options="locations"
    key-attr="identifier"
    text-attr="label"
    :item-height="itemHeight"
    :dense="dense"
    auto-select-first
    v-bind="$attrs"
  >
    <template #item="{ disabled, item }">
      <div
        :id="`balance-location__${item.identifier}`"
        class="flex items-center gap-2 min-w-0"
        :class="[hasPaths ? 'h-10' : 'h-7', { 'opacity-40': disabled }]"
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
        <span class="truncate text-rui-text-secondary">{{ treeStore.pathIfNameShared(item.identifier) ?? item.name }}</span>
      </div>
    </template>
  </RuiAutoComplete>
</template>

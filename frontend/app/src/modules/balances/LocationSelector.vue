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
    :item-height="dense ? 44 : 60"
    :dense="dense"
    auto-select-first
    v-bind="$attrs"
  >
    <template #item="{ disabled, item }">
      <div
        class="flex flex-col"
        :class="{ 'opacity-40': disabled }"
      >
        <LocationIcon
          :id="`balance-location__${item.identifier}`"
          class="!justify-start"
          horizontal
          :item="item.identifier"
        />
        <span
          v-if="item.parentPath"
          class="text-caption text-rui-text-secondary pl-8"
          data-testid="location-option-path"
        >
          {{ item.parentPath }}
        </span>
      </div>
    </template>
    <template #selection="{ item }">
      <LocationIcon
        class="!justify-start pr-2"
        horizontal
        :item="item.identifier"
      />
    </template>
  </RuiAutoComplete>
</template>

<script setup lang="ts">
import type { AssetInfoWithId } from '@rotki/common';
import type { ActiveFilter, FieldDef, FilterOp } from '@/modules/core/table/pill/core/types';
import { startPromise } from '@shared/utils';
import { uniqueObjects } from '@/modules/core/common/data/data';
import { assetDisplayCaption, assetDisplayLabel } from '@/modules/core/common/display/assets';
import PillOperatorToggle from '@/modules/core/table/pill/PillOperatorToggle.vue';
import ValueSelectList, { type SelectOption } from '@/modules/core/table/pill/ValueSelectList.vue';
import AssetIcon from '@/modules/shell/components/AssetIcon.vue';
import { useAssetSearch } from '@/modules/shell/components/inputs/use-asset-search';

const { field, filter } = defineProps<{
  field: FieldDef;
  filter: ActiveFilter;
}>();

const emit = defineEmits<{
  update: [filter: ActiveFilter];
  /** Escape in the list: the editor is done, so the bar can close its popover. */
  close: [];
}>();

const { t } = useI18n({ useScope: 'global' });

const searchModel = computed<string | undefined>(() => (field.multiple ? undefined : filter.values[0]));
const { getVisibleAsset, loading, modelSearch, preload, visibleAssets } = useAssetSearch({ modelValue: searchModel });

const selectedInfo = ref<Map<string, AssetInfoWithId>>(new Map());

const selectedAssets = computed<AssetInfoWithId[]>(() =>
  filter.values.map(value => get(selectedInfo).get(value)).filter((info): info is AssetInfoWithId => info !== undefined),
);

const options = computed<SelectOption[]>(() => {
  const all = uniqueObjects([...get(selectedAssets), ...get(visibleAssets)], asset => asset.identifier)
    .map(asset => ({
      caption: assetDisplayCaption(asset.identifier, asset.name),
      label: assetDisplayLabel(asset.identifier, asset.symbol),
      value: asset.identifier,
    }));
  const isSelected = (option: SelectOption): boolean => filter.values.includes(option.value);
  return [...all.filter(isSelected), ...all.filter(option => !isSelected(option))];
});

const pinnedCount = computed<number>(() => get(options).filter(option => filter.values.includes(option.value)).length);

const selected = computed<string[]>({
  get() {
    return filter.values;
  },
  set(values: string[]) {
    for (const identifier of values) {
      const info = getVisibleAsset(identifier) ?? get(selectedInfo).get(identifier);
      if (info)
        get(selectedInfo).set(identifier, info);
    }
    emit('update', { ...filter, values });
  },
});

function setOperator(op: FilterOp): void {
  emit('update', { ...filter, op });
}

/**
 * Fills the list so it opens on the selected asset's siblings rather than on a single row.
 *
 * @remarks
 * Seeds through `preload` rather than `modelSearch`, which would leave the query as text in the
 * search box for the user to clear. A list that already holds results is left as it is.
 */
function seedVisibleAssets(): void {
  if (get(visibleAssets).length > 0)
    return;

  const [current] = filter.values;
  startPromise(preload(current === undefined ? 'ETH' : field.resolveLabel?.(current) ?? current));
}

onMounted(seedVisibleAssets);
</script>

<template>
  <div class="flex flex-col min-w-64">
    <PillOperatorToggle
      class="m-3 mb-2 self-start"
      :field="field"
      :op="filter.op"
      @update:op="setOperator($event)"
    />

    <ValueSelectList
      v-model="selected"
      v-model:search="modelSearch"
      :options="options"
      no-filter
      :pinned="pinnedCount"
      :loading="loading"
      :multiple="field.multiple"
      :search-placeholder="t('common.actions.search')"
      :empty-text="t('data_table.no_data')"
      @close="emit('close')"
    >
      <template #icon="{ value }">
        <AssetIcon
          :identifier="value"
          size="20px"
          class="shrink-0"
        />
      </template>
    </ValueSelectList>
  </div>
</template>

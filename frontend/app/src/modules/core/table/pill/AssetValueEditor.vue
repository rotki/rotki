<script setup lang="ts">
import type { AssetInfoWithId } from '@rotki/common';
import type { ActiveFilter, FieldDef, FilterOp } from '@/modules/core/table/pill/core/types';
import { startPromise } from '@shared/utils';
import { uniqueObjects } from '@/modules/core/common/data/data';
import { assetDisplayCaption, assetDisplayLabel } from '@/modules/core/common/display/assets';
import { useOperatorLabels } from '@/modules/core/table/pill/composables/use-operator-labels';
import { operatorsFor } from '@/modules/core/table/pill/core/operators';
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
const operatorLabels = useOperatorLabels();

const operators = computed<readonly FilterOp[]>(() => operatorsFor(field));
const showOperators = computed<boolean>(() => get(operators).length > 1);

// The asset the pill already filters on. Handing it to `useAssetSearch` as its selected value is
// what keeps it in the options through every later search (`retainSelectedValueInOptions`), so
// searching for something else can never hide what is currently filtered on. It tracks a single
// value, so a multi-select asset field falls back to `selectedInfo` for the same job.
const searchModel = computed<string | undefined>(() => (field.multiple ? undefined : filter.values[0]));
const { getVisibleAsset, loading, modelSearch, preload, visibleAssets } = useAssetSearch({ modelValue: searchModel });

// Resolved info for every asset selected while the editor has been open, so a selected row keeps
// its symbol and name after the search that surfaced it has been replaced. A pure cache: it is
// never pruned, but only the *currently* selected entries are read out of it below, so an asset
// that was picked and then swapped out does not linger in the list.
const selectedInfo = ref<Map<string, AssetInfoWithId>>(new Map());

const selectedAssets = computed<AssetInfoWithId[]>(() =>
  filter.values.map(value => get(selectedInfo).get(value)).filter((info): info is AssetInfoWithId => info !== undefined),
);

// Selected assets are pinned to the top of the list. Retaining one in the options only puts it
// *somewhere* in fifty search results — a single-select field has no chip row to show it in, so
// without this the asset being filtered on scrolls out of sight the moment the user searches for
// anything else.
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

// How many rows the pinning above put ahead of the search results, so the list highlights the
// first result rather than re-toggling the asset that is already filtered on.
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

function setOperator(op: FilterOp | FilterOp[] | undefined): void {
  if (op !== undefined && !Array.isArray(op))
    emit('update', { ...filter, op });
}

onMounted(() => {
  // Open on a list that is worth reading. With an asset already selected that means its own
  // symbol: the reason to reopen an asset pill is usually to swap it for a sibling — the same
  // symbol on another chain — so those variants should already be there, with the current one
  // pinned and ticked on top. `useAssetSearch` alone would give a list of exactly one row, which
  // is as good as empty. With nothing selected, `ETH` is the seed.
  //
  // Seeding through `preload` rather than `modelSearch` keeps the search box itself empty: a
  // prefilled box is text the user has to clear before typing their own.
  if (get(visibleAssets).length > 0)
    return;

  const [current] = filter.values;
  startPromise(preload(current === undefined ? 'ETH' : field.resolveLabel?.(current) ?? current));
});
</script>

<template>
  <div class="flex flex-col min-w-[16rem]">
    <div
      v-if="showOperators"
      class="p-3 pb-2"
    >
      <RuiButtonGroup
        :model-value="filter.op"
        color="primary"
        size="sm"
        required
        @update:model-value="setOperator($event)"
      >
        <RuiButton
          v-for="op in operators"
          :key="op"
          :model-value="op"
          :data-testid="`op-${op}`"
        >
          {{ operatorLabels[op] }}
        </RuiButton>
      </RuiButtonGroup>
    </div>

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

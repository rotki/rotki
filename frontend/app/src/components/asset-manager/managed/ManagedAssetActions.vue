<script setup lang="ts">
import type { Filters, Matcher } from '@/composables/filters/assets';
import AssetStatusFilter from '@/components/asset-manager/AssetStatusFilter.vue';
import IgnoreButtons from '@/components/history/IgnoreButtons.vue';
import TableFilter from '@/components/table-filter/TableFilter.vue';
import { IgnoredAssetHandlingType, type IgnoredAssetsHandlingType } from '@/types/asset';

interface IgnoredFilter {
  onlyShowOwned: boolean;
  onlyShowWhitelisted: boolean;
  ignoredAssetsHandling: IgnoredAssetsHandlingType;
}

const ignoredFilter = defineModel<IgnoredFilter>('ignoredFilter', { required: true });
const selected = defineModel<string[]>('selected', { required: true });
const filtersModel = defineModel<Filters>('matches', { required: true });

defineProps<{
  ignoredAssets: string[];
  matchers: Matcher[];
}>();

const emit = defineEmits<{
  'ignore': [ignored: boolean];
  'refresh:ignored': [];
}>();

const { t } = useI18n({ useScope: 'global' });

const disabledIgnoreActions = computed<{ ignore: boolean; unIgnore: boolean }>(() => {
  const { ignoredAssetsHandling } = get(ignoredFilter);
  return {
    ignore: ignoredAssetsHandling === IgnoredAssetHandlingType.SHOW_ONLY,
    unIgnore: ignoredAssetsHandling === IgnoredAssetHandlingType.EXCLUDE,
  };
});

function clearSelection() {
  set(selected, []);
}

function handleIgnore(ignored: boolean) {
  emit('ignore', ignored);
}

function handleRefreshIgnored() {
  emit('refresh:ignored');
}
</script>

<template>
  <div class="flex flex-row flex-wrap items-center gap-2 md:mb-4">
    <div class="flex flex-row gap-3">
      <IgnoreButtons
        :disabled="selected.length === 0"
        :disabled-actions="disabledIgnoreActions"
        @ignore="handleIgnore($event)"
      />
      <div
        v-if="selected.length > 0"
        class="flex gap-2 items-center text-sm"
      >
        {{ t('asset_table.selected', { count: selected.length }) }}
        <RuiButton
          size="sm"
          class="!py-0 !px-1.5 !gap-0.5 dark:!bg-opacity-30 dark:!text-white"
          @click="clearSelection()"
        >
          <template #prepend>
            <RuiIcon
              name="lu-x"
              size="14"
            />
          </template>
          {{ t('common.actions.clear_selection') }}
        </RuiButton>
      </div>
    </div>

    <div class="grow" />

    <AssetStatusFilter
      v-model="ignoredFilter"
      :count="ignoredAssets.length"
      @refresh:ignored="handleRefreshIgnored()"
    />

    <div class="w-full lg:w-[25rem]">
      <TableFilter
        v-model:matches="filtersModel"
        :matchers="matchers"
      />
    </div>
  </div>
</template>

<script setup lang="ts" generic="T extends { asset: string }, K extends string">
import type { DataTableColumn, TablePaginationData } from '@rotki/ui-library';
import type { Collection } from '@/modules/core/common/collection';
import type { MatchedKeyword } from '@/modules/core/table/filtering';
import type { FieldDef } from '@/modules/core/table/pill/core/types';
import AssetDetails from '@/modules/assets/AssetDetails.vue';
import { usePillBarLabels } from '@/modules/core/table/pill/composables/use-pill-bar-labels';
import PillFilterBar from '@/modules/core/table/pill/PillFilterBar.vue';
import TableFrame from '@/modules/core/table/TableFrame.vue';
import { useTableEmptyState } from '@/modules/core/table/use-table-empty-state';
import HintMenuIcon from '@/modules/shell/components/HintMenuIcon.vue';
import RowActions from '@/modules/shell/components/RowActions.vue';

/**
 * The table of an asset mapping admin: which symbol a source (an exchange, a counterparty) uses
 * for which asset.
 *
 * @remarks
 * The source column is rendered by the `source` slot, since each kind of source has its own display.
 */
const paginationModel = defineModel<TablePaginationData>('pagination', { required: true });

const filtersModel = defineModel<MatchedKeyword<K>>('filters', { required: true });

const { sourceKey, sourceLabel, symbolKey, subtitle } = defineProps<{
  collection: Collection<T>;
  fields: FieldDef[];
  loading: boolean;
  /** Shown in the toolbar hint. */
  subtitle: string;
  /** The row attribute naming the source, which also keys the rows. */
  sourceKey: keyof T & string;
  sourceLabel: string;
  /** The row attribute holding the symbol the source uses. */
  symbolKey: keyof T & string;
}>();

const emit = defineEmits<{
  edit: [mapping: T];
  delete: [mapping: T];
}>();

defineSlots<{
  source: (props: { row: T }) => any;
}>();

const { t } = useI18n({ useScope: 'global' });
const pillLabels = usePillBarLabels();
const emptyState = useTableEmptyState();

const cols = computed<DataTableColumn<T>[]>(() => [{
  cellClass: 'py-2',
  key: sourceKey,
  label: sourceLabel,
}, {
  cellClass: 'py-2 font-medium',
  key: symbolKey,
  label: t('asset_management.cex_mapping.asset_symbol'),
}, {
  cellClass: 'py-0',
  key: 'asset',
  label: t('asset_management.cex_mapping.recognized_as'),
}, {
  align: 'end',
  cellClass: 'w-px',
  key: 'actions',
  label: t('common.actions_text'),
}]);
</script>

<template>
  <TableFrame>
    <template #toolbar>
      <HintMenuIcon>
        {{ subtitle }}
      </HintMenuIcon>
      <PillFilterBar
        v-model:matches="filtersModel"
        class="flex-1 min-w-48 md:min-w-96"
        :fields="fields"
        :labels="pillLabels"
      />
    </template>
    <RuiDataTable
      v-model:pagination.external="paginationModel"
      :rows="collection.data"
      dense
      :loading="loading"
      :cols="cols"
      :empty="emptyState"
      :row-attr="sourceKey"
    >
      <template #[`item.${sourceKey}`]="{ row }">
        <slot
          name="source"
          :row="row"
        />
      </template>
      <template #item.asset="{ row }">
        <AssetDetails :asset="row.asset" />
      </template>
      <template #item.actions="{ row }">
        <RowActions
          align="end"
          :edit-tooltip="t('asset_table.edit_tooltip')"
          :delete-tooltip="t('asset_table.delete_tooltip')"
          @edit-click="emit('edit', row)"
          @delete-click="emit('delete', row)"
        />
      </template>
    </RuiDataTable>
  </TableFrame>
</template>

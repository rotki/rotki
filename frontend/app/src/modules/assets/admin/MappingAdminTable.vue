<script setup lang="ts" generic="T extends { asset: string }, K extends string">
import type { DataTableColumn, TablePaginationData } from '@rotki/ui-library';
import type { Collection } from '@/modules/core/common/collection';
import type { MatchedKeyword } from '@/modules/core/table/filtering';
import type { FieldDef } from '@/modules/core/table/pill/core/types';
import type { RowDeleteQuestion } from '@/modules/shell/components/row-delete-question';
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

const { collection, deleteConfirm, sourceKey, sourceLabel, symbolKey, subtitle } = defineProps<{
  collection: Collection<T>;
  fields: FieldDef[];
  loading: boolean;
  /** Shown in the toolbar hint. */
  subtitle: string;
  /** The row attribute naming the source; empty for a mapping that applies to every source. */
  sourceKey: keyof T & string;
  sourceLabel: string;
  /** The row attribute holding the symbol the source uses. */
  symbolKey: keyof T & string;
  /** What a row's delete button asks; `delete` is emitted once the user confirms. */
  deleteConfirm: (mapping: T) => RowDeleteQuestion;
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

type KeyedRow = T & { rowKey: string };

/**
 * The rows with a key unique per mapping, and the mapping behind each key.
 *
 * @remarks
 * A mapping is unique on its source and symbol together. The source alone repeats (several
 * mappings for one exchange, and every mapping that applies to all exchanges has no source), so it
 * cannot key the rows. Edit and delete hand back the mapping itself, without the added key.
 */
const keyed = computed<{ rows: KeyedRow[]; byKey: Map<string, T> }>(() => {
  const byKey = new Map<string, T>();
  const rows = collection.data.map((mapping) => {
    const rowKey = `${String(mapping[sourceKey] ?? '')}#${String(mapping[symbolKey])}`;
    byKey.set(rowKey, mapping);
    return { ...mapping, rowKey };
  });
  return { byKey, rows };
});

function emitMapping(event: 'edit' | 'delete', row: KeyedRow): void {
  const mapping = get(keyed).byKey.get(row.rowKey);
  if (!mapping)
    return;

  if (event === 'edit')
    emit('edit', mapping);
  else
    emit('delete', mapping);
}

const cols = computed<DataTableColumn<KeyedRow>[]>(() => [{
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
      :rows="keyed.rows"
      dense
      :loading="loading"
      :cols="cols"
      :empty="emptyState"
      row-attr="rowKey"
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
          :delete-confirm="deleteConfirm(row)"
          @edit-click="emitMapping('edit', row)"
          @delete-click="emitMapping('delete', row)"
        />
      </template>
    </RuiDataTable>
  </TableFrame>
</template>

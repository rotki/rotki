<script setup lang="ts">
import type { DataTableColumn } from '@rotki/ui-library';
import type { UnderlyingToken } from '@rotki/common/lib/data';

defineProps<{ tokens: UnderlyingToken[] }>();

const { t } = useI18n();

const tableHeaders = computed<DataTableColumn<UnderlyingToken>[]>(() => [
  {
    label: t('common.address'),
    key: 'address',
  },
  {
    label: t('underlying_token_manager.tokens.token_kind'),
    key: 'tokenKind',
    cellClass: 'text-no-wrap',
  },
  {
    label: t('underlying_token_manager.tokens.weight'),
    key: 'weight',
    cellClass: 'text-no-wrap',
  },
]);
</script>

<template>
  <RuiCard>
    <template #header>
      {{ t('asset_table.underlying_tokens') }}
    </template>
    <RuiDataTable
      outlined
      :cols="tableHeaders"
      :rows="tokens"
      row-attr="address"
    >
      <template #item.address="{ row }">
        <HashLink
          :text="row.address"
          full-address
        />
      </template>
      <template #item.tokenKind="{ row }">
        {{ row.tokenKind.toUpperCase() }}
      </template>
      <template #item.weight="{ row }">
        {{
          t('underlying_token_manager.tokens.weight_percentage', {
            weight: row.weight,
          })
        }}
      </template>
    </RuiDataTable>
  </RuiCard>
</template>

<script setup lang="ts">
import type { UnderlyingToken } from '@rotki/common';
import type { DataTableColumn } from '@rotki/ui-library';
import HashLink from '@/components/helper/HashLink.vue';

defineProps<{ tokens: UnderlyingToken[] }>();

const { t } = useI18n();

const tableHeaders = computed<DataTableColumn<UnderlyingToken>[]>(() => [
  {
    key: 'address',
    label: t('common.address'),
  },
  {
    cellClass: 'text-no-wrap',
    key: 'tokenKind',
    label: t('underlying_token_manager.tokens.token_kind'),
  },
  {
    cellClass: 'text-no-wrap',
    key: 'weight',
    label: t('underlying_token_manager.tokens.weight'),
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
          type="token"
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

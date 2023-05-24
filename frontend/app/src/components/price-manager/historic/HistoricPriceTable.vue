<script setup lang="ts">
import { type DataTableHeader } from 'vuetify';
import { type HistoricalPrice } from '@/types/prices';

const props = withDefaults(
  defineProps<{
    items: HistoricalPrice[];
    loading?: boolean;
  }>(),
  {
    loading: false
  }
);

const emit = defineEmits<{
  (e: 'edit', item: HistoricalPrice): void;
  (e: 'delete', item: HistoricalPrice): void;
  (e: 'refresh'): void;
}>();

const { items } = toRefs(props);

const { t } = useI18n();

const headers = computed<DataTableHeader[]>(() => [
  {
    text: t('price_table.headers.from_asset'),
    value: 'fromAsset'
  },
  {
    text: '',
    value: 'wasWorth',
    sortable: false
  },
  {
    text: t('common.price'),
    value: 'price',
    align: 'end'
  },
  {
    text: t('price_table.headers.to_asset'),
    value: 'toAsset'
  },
  {
    text: '',
    value: 'on',
    sortable: false
  },
  {
    text: t('common.datetime'),
    value: 'timestamp'
  },
  {
    text: '',
    value: 'actions'
  }
]);

const edit = (item: HistoricalPrice) => {
  emit('edit', item);
};

const deleteItem = (item: HistoricalPrice) => {
  emit('delete', item);
};
const refresh = () => emit('refresh');
</script>

<template>
  <card outlined-body>
    <template #title>
      <refresh-button
        :loading="loading"
        :tooltip="t('price_table.refresh_tooltip')"
        @refresh="refresh()"
      />
      <div>
        {{ t('price_table.historic.title') }}
      </div>
    </template>
    <slot />
    <data-table
      :items="items"
      :headers="headers"
      :loading="loading"
      sort-by="timestamp"
    >
      <template #item.fromAsset="{ item }">
        <asset-details :asset="item.fromAsset" />
      </template>
      <template #item.toAsset="{ item }">
        <asset-details :asset="item.toAsset" />
      </template>
      <template #item.timestamp="{ item }">
        <date-display :timestamp="item.timestamp" />
      </template>
      <template #item.price="{ item }">
        <amount-display :value="item.price" />
      </template>
      <template #item.wasWorth>{{ t('price_table.was_worth') }}</template>
      <template #item.on>{{ t('price_table.on') }}</template>
      <template #item.actions="{ item }">
        <row-actions
          :disabled="loading"
          :delete-tooltip="t('price_table.actions.delete.tooltip')"
          :edit-tooltip="t('price_table.actions.edit.tooltip')"
          @delete-click="deleteItem(item)"
          @edit-click="edit(item)"
        />
      </template>
    </data-table>
  </card>
</template>

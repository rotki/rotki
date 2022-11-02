<template>
  <card outlined-body>
    <template #title>
      {{ tc('common.assets') }}
    </template>
    <template #subtitle>
      {{ tc('asset_table.custom.subtitle') }}
    </template>
    <template #actions>
      <v-row>
        <v-col />
        <v-col cols="12" md="6" class="pb-md-8">
          <table-filter
            :matchers="matchers"
            data-cy="asset_table_filter"
            @update:matches="updateFilter"
          />
        </v-col>
      </v-row>
    </template>
    <v-btn
      absolute
      fab
      top
      right
      dark
      color="primary"
      data-cy="add-manual-asset"
      @click="add"
    >
      <v-icon> mdi-plus </v-icon>
    </v-btn>
    <data-table
      :items="assets"
      :loading="loading"
      :headers="tableHeaders"
      single-expand
      :expanded="expanded"
      item-key="identifier"
      sort-by="name"
      class="custom-assets-table"
      :sort-desc="false"
      :server-items-length="serverItemLength"
      @update:options="updatePaginationHandler($event)"
    >
      <template #item.custom_asset_type="{ item }">
        <badge-display>
          {{ item.customAssetType }}
        </badge-display>
      </template>
      <template #item.actions="{ item }">
        <row-actions
          :edit-tooltip="tc('asset_table.edit_tooltip')"
          :delete-tooltip="tc('asset_table.delete_tooltip')"
          @edit-click="edit(item)"
          @delete-click="deleteAsset(item)"
        >
          <copy-button
            class="mx-1"
            :tooltip="tc('asset_table.copy_identifier.tooltip')"
            :value="item.identifier"
          />
        </row-actions>
      </template>
      <template #expanded-item="{ item }">
        <table-expand-container visible :colspan="tableHeaders.length">
          <div class="font-weight-bold">{{ tc('asset_table.notes') }}:</div>
          <div class="pt-2">
            {{ item.notes }}
          </div>
        </table-expand-container>
      </template>
      <template #item.expand="{ item }">
        <row-expander
          v-if="item.notes"
          :expanded="expanded.includes(item)"
          @click="expanded = expanded.includes(item) ? [] : [item]"
        />
      </template>
    </data-table>
  </card>
</template>

<script setup lang="ts">
import { SupportedAsset } from '@rotki/common/lib/data';
import { PropType, Ref } from 'vue';
import { DataTableHeader } from 'vuetify';
import CopyButton from '@/components/helper/CopyButton.vue';
import RowActions from '@/components/helper/RowActions.vue';
import RowExpander from '@/components/helper/RowExpander.vue';
import { useCustomAssetFilter } from '@/composables/filters/custom-assets';
import { useFrontendSettingsStore } from '@/store/settings/frontend';
import {
  CustomAsset,
  CustomAssetPagination,
  CustomAssetPaginationOptions,
  defaultCustomAssetPagination
} from '@/types/assets';
import { convertPagination } from '@/types/pagination';

const props = defineProps({
  assets: { required: true, type: Array as PropType<CustomAsset[]> },
  loading: { required: false, type: Boolean, default: false },
  serverItemLength: { required: true, type: Number },
  types: { required: true, type: Array as PropType<string[]> }
});

const { types } = toRefs(props);

const emit = defineEmits<{
  (e: 'add'): void;
  (e: 'edit', asset: CustomAsset): void;
  (e: 'delete-asset', asset: CustomAsset): void;
  (e: 'update:pagination', pagination: CustomAssetPagination): void;
}>();

const { itemsPerPage } = storeToRefs(useFrontendSettingsStore());
const { filters, matchers, updateFilter } = useCustomAssetFilter(types);

const expanded: Ref<SupportedAsset[]> = ref([]);

const options: Ref<CustomAssetPaginationOptions> = ref(
  defaultCustomAssetPagination(get(itemsPerPage))
);

const { tc } = useI18n();

const tableHeaders = computed<DataTableHeader[]>(() => [
  {
    text: tc('common.asset'),
    value: 'name',
    width: '50%'
  },
  {
    text: tc('common.type'),
    value: 'custom_asset_type',
    width: '50%'
  },
  {
    text: '',
    value: 'actions',
    sortable: false
  },
  {
    text: '',
    width: '48px',
    value: 'expand',
    sortable: false
  }
]);

const add = () => emit('add');
const edit = (asset: CustomAsset) => emit('edit', asset);
const deleteAsset = (asset: CustomAsset) => emit('delete-asset', asset);

const updatePaginationHandler = (
  updateOptions: CustomAssetPaginationOptions
) => {
  set(options, updateOptions);
};

watch([options, filters] as const, ([options, filters]) => {
  let apiPagination = convertPagination<CustomAsset>(
    options,
    'name'
  ) as CustomAssetPagination;

  emit('update:pagination', {
    ...apiPagination,
    name: filters.name as string | undefined,
    customAssetType: filters.custom_asset_type as string | undefined
  });
});
</script>

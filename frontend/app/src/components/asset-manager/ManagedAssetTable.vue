<template>
  <card outlined-body>
    <template #title>
      {{ tc('common.assets') }}
    </template>
    <template #subtitle>
      {{ tc('asset_table.managed.subtitle') }}
    </template>
    <template #actions>
      <v-row>
        <v-col cols="12" md="4">
          <ignore-buttons
            :disabled="selected.length === 0"
            @ignore="massIgnore"
          />
          <div v-if="selected.length > 0" class="mt-2 ms-1">
            {{ tc('asset_table.selected', 0, { count: selected.length }) }}
            <v-btn small text @click="selected = []">
              {{ tc('common.actions.clear_selection') }}
            </v-btn>
          </div>
        </v-col>
        <v-col />
        <v-col cols="12" md="auto">
          <v-menu offset-y :close-on-content-click="false">
            <template #activator="{ on }">
              <v-btn outlined text height="40px" v-on="on">
                {{ tc('common.actions.filter') }}
                <v-icon class="ml-2">mdi-chevron-down</v-icon>
              </v-btn>
            </template>
            <v-list>
              <v-list-item link @click="onlyShowOwned = !onlyShowOwned">
                <v-checkbox
                  :input-value="onlyShowOwned"
                  class="mt-0 py-2"
                  :label="tc('asset_table.only_show_owned')"
                  hide-details
                />
              </v-list-item>
              <v-list-item
                :class="css['filter-heading']"
                class="font-weight-bold text-uppercase py-2"
              >
                {{ tc('asset_table.filter_by_ignored_status') }}
              </v-list-item>
              <v-list-item>
                <v-radio-group v-model="ignoredAssetsHandling" class="mt-0">
                  <v-radio value="none" :label="tc('asset_table.show_all')" />
                  <v-radio
                    value="exclude"
                    :label="tc('asset_table.only_show_unignored')"
                  />
                  <v-radio
                    value="show_only"
                    :label="tc('asset_table.only_show_ignored')"
                  />
                </v-radio-group>
              </v-list-item>
            </v-list>
          </v-menu>
        </v-col>
        <v-col cols="12" md="4" class="pb-md-8">
          <table-filter
            :matchers="matchers"
            data-cy="asset_table_filter"
            @update:matches="updateFilter"
          />
        </v-col>
      </v-row>
    </template>
    <v-btn absolute fab top right dark color="primary" @click="add">
      <v-icon> mdi-plus </v-icon>
    </v-btn>
    <data-table
      v-model="selected"
      :items="tokens"
      :loading="loading"
      :headers="tableHeaders"
      single-expand
      :expanded="expanded"
      item-key="identifier"
      sort-by="symbol"
      :sort-desc="false"
      :server-items-length="serverItemLength"
      :single-select="false"
      show-select
      :options="options"
      @update:options="updatePaginationHandler($event)"
    >
      <template #item.symbol="{ item }">
        <asset-details-base
          :changeable="change"
          opens-details
          :asset="getAsset(item)"
        />
      </template>
      <template #item.address="{ item }">
        <hash-link v-if="item.address" :text="item.address" />
      </template>
      <template #item.started="{ item }">
        <date-display v-if="item.started" :timestamp="item.started" />
        <span v-else>-</span>
      </template>
      <template #item.type="{ item }">
        {{ formatType(item.type) }}
      </template>
      <template #item.ignored="{ item }">
        <div class="d-flex justify-center">
          <v-switch
            :input-value="isIgnored(item.identifier)"
            @change="toggleIgnoreAsset(item.identifier)"
          />
        </div>
      </template>
      <template #item.actions="{ item }">
        <row-actions
          v-if="item.type !== CUSTOM_ASSET"
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
      <template #expanded-item="{ item, headers }">
        <asset-underlying-tokens :cols="headers.length" :asset="item" />
      </template>
      <template #item.expand="{ item }">
        <row-expander
          v-if="item.underlyingTokens && item.underlyingTokens.length > 0"
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
import AssetUnderlyingTokens from '@/components/asset-manager/AssetUnderlyingTokens.vue';
import AssetDetailsBase from '@/components/helper/AssetDetailsBase.vue';
import CopyButton from '@/components/helper/CopyButton.vue';
import DataTable from '@/components/helper/DataTable.vue';
import RowActions from '@/components/helper/RowActions.vue';
import RowExpander from '@/components/helper/RowExpander.vue';
import IgnoreButtons from '@/components/history/IgnoreButtons.vue';
import { useAssetFilter } from '@/composables/filters/assets';
import { CUSTOM_ASSET } from '@/services/assets/consts';
import { useIgnoredAssetsStore } from '@/store/assets/ignored';
import { useMessageStore } from '@/store/message';
import { useFrontendSettingsStore } from '@/store/settings/frontend';
import { ActionStatus } from '@/store/types';
import {
  AssetPagination,
  AssetPaginationOptions,
  defaultAssetPagination
} from '@/types/assets';
import { convertPagination } from '@/types/pagination';
import { getAddressFromEvmIdentifier, isEvmIdentifier } from '@/utils/assets';
import { uniqueStrings } from '@/utils/data';
import { toSentenceCase } from '@/utils/text';

defineProps({
  tokens: { required: true, type: Array as PropType<SupportedAsset[]> },
  loading: { required: false, type: Boolean, default: false },
  change: { required: true, type: Boolean },
  serverItemLength: { required: true, type: Number }
});

const emit = defineEmits<{
  (e: 'add'): void;
  (e: 'edit', asset: SupportedAsset): void;
  (e: 'delete-asset', asset: SupportedAsset): void;
  (e: 'update:pagination', pagination: AssetPagination): void;
}>();

const { itemsPerPage } = storeToRefs(useFrontendSettingsStore());
const { filters, matchers, updateFilter } = useAssetFilter();

const expanded: Ref<SupportedAsset[]> = ref([]);
const selected: Ref<SupportedAsset[]> = ref([]);
const onlyShowOwned = ref<boolean>(false);
const ignoredAssetsHandling = ref<'none' | 'exclude' | 'show_only'>('exclude');
const options: Ref<AssetPaginationOptions> = ref(
  defaultAssetPagination(get(itemsPerPage))
);

const { tc } = useI18n();

const tableHeaders = computed<DataTableHeader[]>(() => [
  {
    text: tc('common.asset'),
    value: 'symbol'
  },
  {
    text: tc('common.type'),
    value: 'type'
  },
  {
    text: tc('common.address'),
    value: 'address'
  },
  {
    text: tc('asset_table.headers.started'),
    value: 'started'
  },
  {
    text: tc('assets.ignore'),
    value: 'ignored',
    align: 'center',
    sortable: false
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

const isIgnored = (identifier: string) => {
  return isAssetIgnored(identifier);
};

const add = () => emit('add');
const edit = (asset: SupportedAsset) => emit('edit', asset);
const deleteAsset = (asset: SupportedAsset) => emit('delete-asset', asset);

const { setMessage } = useMessageStore();
const { isAssetIgnored, ignoreAsset, unignoreAsset } = useIgnoredAssetsStore();

const formatType = (string?: string) => {
  return toSentenceCase(string ?? 'EVM token');
};

const getAsset = (item: SupportedAsset) => {
  const name =
    item.name ??
    item.symbol ??
    (isEvmIdentifier(item.identifier)
      ? getAddressFromEvmIdentifier(item.identifier)
      : item.identifier);

  return {
    name,
    symbol: item.symbol ?? '',
    identifier: item.identifier,
    isCustomAsset: item.type === CUSTOM_ASSET,
    customAssetType: item.customAssetType ?? ''
  };
};

const toggleIgnoreAsset = async (identifier: string) => {
  if (get(isIgnored(identifier))) {
    await unignoreAsset(get(identifier));
  } else {
    await ignoreAsset(get(identifier));
  }
};

const massIgnore = async (ignored: boolean) => {
  const ids = get(selected)
    .filter(item => {
      const isItemIgnored = get(isIgnored(item.identifier));
      return ignored ? !isItemIgnored : isItemIgnored;
    })
    .map(item => item.identifier)
    .filter(uniqueStrings);

  let status: ActionStatus;

  if (ids.length === 0) {
    const choice = ignored ? 1 : 2;
    setMessage({
      success: false,
      title: tc('ignore.no_items.title', choice),
      description: tc('ignore.no_items.description', choice)
    });
    return;
  }

  if (ignored) {
    status = await ignoreAsset(ids);
  } else {
    status = await unignoreAsset(ids);
  }

  if (status.success) {
    set(selected, []);
  }
};

const updatePaginationHandler = (updateOptions: AssetPaginationOptions) => {
  set(options, updateOptions);

  let apiPagination = convertPagination<SupportedAsset>(
    updateOptions,
    'symbol'
  ) as AssetPagination;
  const filter = get(filters);
  const onlyOwned = get(onlyShowOwned);
  const ignored = get(ignoredAssetsHandling);

  emit('update:pagination', {
    ...apiPagination,
    symbol: filter.symbol as string | undefined,
    name: filter.name as string | undefined,
    showUserOwnedAssetsOnly: onlyOwned,
    ignoredAssetsHandling: ignored
  });
};

watch([filters, onlyShowOwned, ignoredAssetsHandling], () => {
  const pageOptions = get(options);
  if (pageOptions) {
    updatePaginationHandler({
      ...pageOptions,
      page: 1
    });
  }
});

const css = useCssModule();
</script>

<style module lang="scss">
.filter-heading {
  font-size: 0.875rem;
  min-height: auto;
}
</style>

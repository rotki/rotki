<script setup lang="ts">
import { isEqual } from 'lodash-es';
import { type SupportedAsset } from '@rotki/common/lib/data';
import { type Collection } from '@/types/collection';
import { type Nullable } from '@/types';
import {
  type AssetRequestPayload,
  type IgnoredAssetsHandlingType
} from '@/types/asset';
import { type Filters, type Matcher } from '@/composables/filters/assets';

const props = withDefaults(
  defineProps<{
    identifier?: string | null;
    mainPage?: boolean;
  }>(),
  { identifier: null, mainPage: false }
);

const { identifier, mainPage } = toRefs(props);

const mergeTool = ref<boolean>(false);
const ignoredFilter = ref<{
  onlyShowOwned: boolean;
  ignoredAssetsHandling: IgnoredAssetsHandlingType;
}>({
  onlyShowOwned: false,
  ignoredAssetsHandling: 'exclude'
});

const extraParams = computed(() => {
  const { ignoredAssetsHandling, onlyShowOwned } = get(ignoredFilter);
  return {
    ignoredAssetsHandling,
    showUserOwnedAssetsOnly: onlyShowOwned.toString()
  };
});

const dialogTitle = computed<string>(() =>
  get(editableItem)
    ? t('asset_management.edit_title')
    : t('asset_management.add_title')
);

const router = useRouter();
const route = useRoute();
const { t } = useI18n();
const { queryAllAssets, deleteAsset } = useAssetManagementApi();
const { setMessage } = useMessageStore();
const { show } = useConfirmStore();
const { ignoredAssets } = storeToRefs(useIgnoredAssetsStore());

const { setOpenDialog, setPostSubmitFunc } = useManagedAssetForm();

const add = () => {
  set(editableItem, null);
  setOpenDialog(true);
};

const edit = (editAsset: SupportedAsset) => {
  set(editableItem, editAsset);
  setOpenDialog(true);
};

const editAsset = async (assetId: Nullable<string>) => {
  if (assetId) {
    const all = await queryAllAssets({
      identifiers: [assetId],
      limit: 1,
      offset: 0
    });

    const foundAsset = all.data[0];
    if (foundAsset) {
      edit(foundAsset);
    }
  }
};

const { deleteCacheKey } = useAssetCacheStore();

const deleteAssetHandler = async (identifier: string) => {
  try {
    const success = await deleteAsset(identifier);
    if (success) {
      await fetchData();
      deleteCacheKey(identifier);
    }
  } catch (e: any) {
    setMessage({
      description: t('asset_management.delete_error', {
        address: identifier,
        message: e.message
      })
    });
  }
};

const confirmDelete = async (toDeleteAsset: SupportedAsset) => {
  await deleteAssetHandler(toDeleteAsset.identifier);
};

watch(ignoredFilter, async (oldValue, newValue) => {
  if (!isEqual(oldValue, newValue)) {
    setPage(1);
  }
});

const {
  filters,
  matchers,
  expanded,
  selected,
  state: assets,
  isLoading: loading,
  editableItem,
  options,
  fetchData,
  setOptions,
  setFilter,
  setPage
} = usePaginationFilters<
  SupportedAsset,
  AssetRequestPayload,
  SupportedAsset,
  Collection<SupportedAsset>,
  Filters,
  Matcher
>(null, mainPage, useAssetFilter, queryAllAssets, {
  onUpdateFilters(query) {
    set(ignoredFilter, {
      onlyShowOwned: query.showUserOwnedAssetsOnly === 'true',
      ignoredAssetsHandling: query.ignoredAssetsHandling || 'exclude'
    });
  },
  extraParams,
  defaultSortBy: {
    key: 'symbol',
    ascending: [true]
  }
});

setPostSubmitFunc(fetchData);

const showDeleteConfirmation = (item: SupportedAsset) => {
  show(
    {
      title: t('asset_management.confirm_delete.title'),
      message: t('asset_management.confirm_delete.message', {
        asset: item?.symbol ?? ''
      })
    },
    async () => await confirmDelete(item)
  );
};

onMounted(async () => {
  await fetchData();
  const idToEdit = get(identifier);
  const query = get(route).query;

  if (idToEdit || query.add) {
    if (idToEdit) {
      await editAsset(get(identifier));
    } else {
      add();
    }
    await router.replace({ query: {} });
  }
});

watch(identifier, async assetId => {
  await editAsset(assetId);
});
</script>

<template>
  <TablePageLayout
    :title="[
      t('navigation_menu.manage_assets'),
      t('navigation_menu.manage_assets_sub.managed_assets')
    ]"
  >
    <template #buttons>
      <RuiButton
        color="primary"
        variant="outlined"
        :loading="loading"
        @click="fetchData()"
      >
        <template #prepend>
          <RuiIcon name="refresh-line" />
        </template>
        {{ t('common.refresh') }}
      </RuiButton>

      <RuiButton data-cy="managed-asset-add-btn" color="primary" @click="add()">
        <template #prepend>
          <RuiIcon name="add-line" />
        </template>
        {{ t('managed_asset_content.add_asset') }}
      </RuiButton>
      <VMenu offset-y left :close-on-content-click="false">
        <template #activator="{ on }">
          <RuiButton variant="text" icon size="sm" class="!p-2" v-on="on">
            <RuiIcon name="more-2-fill" />
          </RuiButton>
        </template>
        <VList>
          <RestoreAssetDbButton dropdown />
          <RuiTooltip
            :open-delay="400"
            class="w-full"
            :popper="{ placement: 'left' }"
            tooltip-class="max-w-[200px]"
          >
            <template #activator>
              <RuiButton variant="list" @click="mergeTool = true">
                <template #prepend>
                  <RuiIcon name="git-merge-line" />
                </template>
                {{ t('asset_management.merge_assets') }}
              </RuiButton>
            </template>
            {{ t('asset_management.merge_assets_tooltip') }}
          </RuiTooltip>
        </VList>
      </VMenu>
    </template>

    <RuiCard>
      <MergeDialog v-model="mergeTool" />

      <ManagedAssetTable
        :tokens="assets.data"
        :loading="loading"
        :change="!loading"
        :server-item-length="assets.found"
        :filters="filters"
        :matchers="matchers"
        :ignored-assets="ignoredAssets"
        :ignored-filter="ignoredFilter"
        :expanded="expanded"
        :selected="selected"
        :options="options"
        @refresh="fetchData()"
        @edit="edit($event)"
        @delete-asset="showDeleteConfirmation($event)"
        @update:pagination="setOptions($event)"
        @update:filters="setFilter($event)"
        @update:expanded="expanded = $event"
        @update:selected="selected = $event"
        @update:ignored-filter="ignoredFilter = $event"
      />

      <ManagedAssetFormDialog
        :title="dialogTitle"
        :editable-item="editableItem"
      />
    </RuiCard>
  </TablePageLayout>
</template>

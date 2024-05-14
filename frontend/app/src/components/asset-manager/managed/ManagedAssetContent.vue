<script setup lang="ts">
import { isEqual, keyBy } from 'lodash-es';
import type { SupportedAsset } from '@rotki/common/lib/data';
import type { Collection } from '@/types/collection';
import type { Nullable } from '@/types';
import type {
  AssetRequestPayload,
  IgnoredAssetsHandlingType,
} from '@/types/asset';
import type { Filters, Matcher } from '@/composables/filters/assets';

const props = withDefaults(
  defineProps<{
    identifier?: string | null;
    mainPage?: boolean;
  }>(),
  { identifier: null, mainPage: false },
);

const { t } = useI18n();

const { identifier, mainPage } = toRefs(props);

const mergeTool = ref<boolean>(false);
const ignoredFilter = ref<{
  onlyShowOwned: boolean;
  onlyShowWhitelisted: boolean;
  ignoredAssetsHandling: IgnoredAssetsHandlingType;
}>({
  onlyShowOwned: false,
  onlyShowWhitelisted: false,
  ignoredAssetsHandling: 'exclude',
});

const extraParams = computed(() => {
  const { ignoredAssetsHandling, onlyShowOwned, onlyShowWhitelisted }
    = get(ignoredFilter);
  return {
    ignoredAssetsHandling,
    showUserOwnedAssetsOnly: onlyShowOwned.toString(),
    showWhitelistedAssetsOnly: onlyShowWhitelisted.toString(),
  };
});

const router = useRouter();
const route = useRoute();
const { queryAllAssets, deleteAsset } = useAssetManagementApi();
const { setMessage } = useMessageStore();
const { show } = useConfirmStore();
const { ignoredAssets } = storeToRefs(useIgnoredAssetsStore());

const { setOpenDialog, setPostSubmitFunc } = useManagedAssetForm();

const { deleteCacheKey } = useAssetCacheStore();

async function confirmDelete(toDeleteAsset: SupportedAsset) {
  await deleteAssetHandler(toDeleteAsset.identifier);
}

const {
  filters,
  matchers,
  expanded,
  selected,
  state: assets,
  isLoading: loading,
  editableItem,
  fetchData,
  setFilter,
  setPage,
  sort,
  pagination,
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
      onlyShowWhitelisted: query.showWhitelistedAssetsOnly === 'true',
      ignoredAssetsHandling: query.ignoredAssetsHandling || 'exclude',
    });
  },
  extraParams,
  defaultSortBy: {
    key: 'symbol',
    ascending: [true],
  },
});

const dialogTitle = computed<string>(() =>
  get(editableItem)
    ? t('asset_management.edit_title')
    : t('asset_management.add_title'),
);

function add() {
  set(editableItem, null);
  setOpenDialog(true);
}

function edit(editAsset: SupportedAsset) {
  set(editableItem, editAsset);
  setOpenDialog(true);
}

async function editAsset(assetId: Nullable<string>) {
  if (assetId) {
    const all = await queryAllAssets({
      identifiers: [assetId],
      limit: 1,
      offset: 0,
    });

    const foundAsset = all.data[0];
    if (foundAsset)
      edit(foundAsset);
  }
}

async function deleteAssetHandler(identifier: string) {
  try {
    const success = await deleteAsset(identifier);
    if (success) {
      await fetchData();
      deleteCacheKey(identifier);
    }
  }
  catch (error: any) {
    setMessage({
      description: t('asset_management.delete_error', {
        address: identifier,
        message: error.message,
      }),
    });
  }
}

setPostSubmitFunc(fetchData);

const assetsMap = computed(() => keyBy(get(assets).data, 'identifier'));

const selectedRows = computed({
  get() {
    return get(selected).map(({ identifier }) => identifier);
  },
  set(identifiers: string[]) {
    set(
      selected,
      identifiers.map(identifier => get(assetsMap)[identifier]),
    );
  },
});

function showDeleteConfirmation(item: SupportedAsset) {
  show(
    {
      title: t('asset_management.confirm_delete.title'),
      message: t('asset_management.confirm_delete.message', {
        asset: item?.symbol ?? '',
      }),
    },
    async () => await confirmDelete(item),
  );
}

onMounted(async () => {
  await fetchData();
  const idToEdit = get(identifier);
  const query = get(route).query;

  if (idToEdit || query.add) {
    if (idToEdit)
      await editAsset(get(identifier));
    else
      add();

    await router.replace({ query: {} });
  }
});

watch(identifier, async (assetId) => {
  await editAsset(assetId);
});

watch(ignoredFilter, (oldValue, newValue) => {
  if (!isEqual(oldValue, newValue))
    setPage(1);
});
</script>

<template>
  <TablePageLayout
    :title="[
      t('navigation_menu.manage_assets'),
      t('navigation_menu.manage_assets_sub.assets'),
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

      <RuiButton
        data-cy="managed-asset-add-btn"
        color="primary"
        @click="add()"
      >
        <template #prepend>
          <RuiIcon name="add-line" />
        </template>
        {{ t('managed_asset_content.add_asset') }}
      </RuiButton>
      <RuiMenu
        :popper="{ placement: 'bottom-end' }"
      >
        <template #activator="{ on }">
          <RuiButton
            variant="text"
            icon
            size="sm"
            class="!p-2"
            v-on="on"
          >
            <RuiIcon name="more-2-fill" />
          </RuiButton>
        </template>
        <div class="py-2">
          <RestoreAssetDbButton dropdown />
          <RuiTooltip
            :open-delay="400"
            class="w-full"
            :popper="{ placement: 'left' }"
            tooltip-class="max-w-[200px]"
          >
            <template #activator>
              <RuiButton
                variant="list"
                @click="mergeTool = true"
              >
                <template #prepend>
                  <RuiIcon name="git-merge-line" />
                </template>
                {{ t('asset_management.merge_assets') }}
              </RuiButton>
            </template>
            {{ t('asset_management.merge_assets_tooltip') }}
          </RuiTooltip>
        </div>
      </RuiMenu>
    </template>

    <RuiCard>
      <MergeDialog v-model="mergeTool" />

      <ManagedAssetTable
        :collection="assets"
        :loading="loading"
        :change="!loading"
        :filters="filters"
        :matchers="matchers"
        :ignored-assets="ignoredAssets"
        :ignored-filter.sync="ignoredFilter"
        :expanded.sync="expanded"
        :selected.sync="selectedRows"
        :pagination.sync="pagination"
        :sort.sync="sort"
        @refresh="fetchData()"
        @edit="edit($event)"
        @delete-asset="showDeleteConfirmation($event)"
        @update:filters="setFilter($event)"
        @update:page="setPage($event)"
      />

      <ManagedAssetFormDialog
        :title="dialogTitle"
        :editable-item="editableItem"
      />
    </RuiCard>
  </TablePageLayout>
</template>

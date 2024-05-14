<script setup lang="ts">
import type { Nullable } from '@/types';
import type { Collection } from '@/types/collection';
import type {
  Filters,
  Matcher,
} from '@/composables/filters/custom-assets';
import type {
  CustomAsset,
  CustomAssetRequestPayload,
} from '@/types/asset';

const props = withDefaults(
  defineProps<{
    identifier?: string | null;
    mainPage?: boolean;
  }>(),
  { identifier: null, mainPage: false },
);

const { t } = useI18n();

const { identifier, mainPage } = toRefs(props);

const types = ref<string[]>([]);

const router = useRouter();
const route = useRoute();

const { deleteCustomAsset, queryAllCustomAssets, getCustomAssetTypes } = useAssetManagementApi();
const { setMessage } = useMessageStore();

const { show } = useConfirmStore();

const { setOpenDialog, setPostSubmitFunc } = useCustomAssetForm();

async function deleteAsset(assetId: string) {
  try {
    const success = await deleteCustomAsset(assetId);
    if (success)
      await refresh();
  }
  catch (error: any) {
    setMessage({
      description: t('asset_management.delete_error', {
        address: assetId,
        message: error.message,
      }),
    });
  }
}

const {
  state,
  filters,
  expanded,
  matchers,
  fetchData,
  setFilter,
  isLoading: loading,
  editableItem,
  pagination,
  sort,
} = usePaginationFilters<
  CustomAsset,
  CustomAssetRequestPayload,
  CustomAsset,
  Collection<CustomAsset>,
  Filters,
  Matcher
>(null, mainPage, () => useCustomAssetFilter(types), queryAllCustomAssets, {
  defaultSortBy: {
    key: 'name',
    ascending: [false],
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

function edit(editAsset: CustomAsset) {
  set(editableItem, editAsset);
  setOpenDialog(true);
}

function editAsset(assetId: Nullable<string>) {
  if (assetId) {
    const asset = get(state).data.find(({ identifier: id }) => id === assetId);
    if (asset)
      edit(asset);
  }
}

async function refreshTypes() {
  set(types, await getCustomAssetTypes());
}

async function refresh() {
  await Promise.all([fetchData(), refreshTypes()]);
}

setPostSubmitFunc(refresh);

function showDeleteConfirmation(item: CustomAsset) {
  show(
    {
      title: t('asset_management.confirm_delete.title'),
      message: t('asset_management.confirm_delete.message', {
        asset: item?.name ?? '',
      }),
    },
    async () => await deleteAsset(item.identifier),
  );
}

onMounted(async () => {
  await refresh();
  editAsset(get(identifier));

  const query = get(route).query;
  if (query.add) {
    add();
    await router.replace({ query: {} });
  }
});

watch(identifier, (assetId) => {
  editAsset(assetId);
});
</script>

<template>
  <TablePageLayout
    :title="[
      t('navigation_menu.manage_assets'),
      t('navigation_menu.manage_assets_sub.custom_assets'),
    ]"
  >
    <template #buttons>
      <RuiButton
        color="primary"
        variant="outlined"
        :loading="loading"
        @click="refresh()"
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
    </template>
    <CustomAssetTable
      :assets="state.data"
      :loading="loading"
      :server-item-length="state.found"
      :filters="filters"
      :matchers="matchers"
      :expanded.sync="expanded"
      :pagination.sync="pagination"
      :sort.sync="sort"
      @edit="edit($event)"
      @delete-asset="showDeleteConfirmation($event)"
      @update:filters="setFilter($event)"
    />
    <CustomAssetFormDialog
      :title="dialogTitle"
      :types="types"
      :editable-item="editableItem"
    />
  </TablePageLayout>
</template>

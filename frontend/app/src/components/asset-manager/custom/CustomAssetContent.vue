<script setup lang="ts">
import { type Nullable } from '@/types';
import { type Collection } from '@/types/collection';
import {
  type Filters,
  type Matcher
} from '@/composables/filters/custom-assets';
import {
  type CustomAsset,
  type CustomAssetRequestPayload
} from '@/types/asset';

const props = withDefaults(
  defineProps<{
    identifier?: string | null;
    mainPage?: boolean;
  }>(),
  { identifier: null, mainPage: false }
);

const { identifier, mainPage } = toRefs(props);

const types = ref<string[]>([]);

const dialogTitle = computed<string>(() =>
  get(editableItem)
    ? t('asset_management.edit_title')
    : t('asset_management.add_title')
);

const router = useRouter();
const route = useRoute();
const { t } = useI18n();
const { deleteCustomAsset, queryAllCustomAssets, getCustomAssetTypes } =
  useAssetManagementApi();
const { setMessage } = useMessageStore();

const { show } = useConfirmStore();

const { setOpenDialog, setPostSubmitFunc } = useCustomAssetForm();

const add = () => {
  set(editableItem, null);
  setOpenDialog(true);
};

const edit = (editAsset: CustomAsset) => {
  set(editableItem, editAsset);
  setOpenDialog(true);
};

const deleteAsset = async (assetId: string) => {
  try {
    const success = await deleteCustomAsset(assetId);
    if (success) {
      await refresh();
    }
  } catch (e: any) {
    setMessage({
      description: t('asset_management.delete_error', {
        address: assetId,
        message: e.message
      })
    });
  }
};

const editAsset = (assetId: Nullable<string>) => {
  if (assetId) {
    const asset = get(state).data.find(({ identifier: id }) => id === assetId);
    if (asset) {
      edit(asset);
    }
  }
};

const {
  state,
  filters,
  expanded,
  matchers,
  options,
  fetchData,
  setFilter,
  setOptions,
  isLoading: loading,
  editableItem
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
    ascending: [false]
  }
});

const refreshTypes = async () => {
  set(types, await getCustomAssetTypes());
};

const refresh = async () => {
  await Promise.all([fetchData(), refreshTypes()]);
};

setPostSubmitFunc(refresh);

const showDeleteConfirmation = (item: CustomAsset) => {
  show(
    {
      title: t('asset_management.confirm_delete.title'),
      message: t('asset_management.confirm_delete.message', {
        asset: item?.name ?? ''
      })
    },
    async () => await deleteAsset(item.identifier)
  );
};

onMounted(async () => {
  await refresh();
  editAsset(get(identifier));

  const query = get(route).query;
  if (query.add) {
    add();
    await router.replace({ query: {} });
  }
});

watch(identifier, assetId => {
  editAsset(assetId);
});
</script>

<template>
  <TablePageLayout>
    <template #title>
      <span class="text-rui-text-secondary">
        {{ t('navigation_menu.manage_assets') }} /
      </span>
      {{ t('navigation_menu.manage_assets_sub.custom_assets') }}
    </template>
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

      <RuiButton data-cy="managed-asset-add-btn" color="primary" @click="add()">
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
      :expanded="expanded"
      :options="options"
      @edit="edit($event)"
      @delete-asset="showDeleteConfirmation($event)"
      @update:pagination="setOptions($event)"
      @update:filters="setFilter($event)"
      @update:expanded="expanded = $event"
    />
    <CustomAssetFormDialog
      :title="dialogTitle"
      :types="types"
      :editable-item="editableItem"
    />
  </TablePageLayout>
</template>

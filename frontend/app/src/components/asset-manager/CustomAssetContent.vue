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
const editableItem = ref<CustomAsset | null>(null);

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
  setOpenDialog(true);
  set(editableItem, null);
};

const edit = (editAsset: CustomAsset) => {
  setOpenDialog(true);
  set(editableItem, editAsset);
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
  isLoading: loading
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
  <v-container>
    <refresh-header
      :title="t('asset_management.custom.title')"
      :loading="loading"
      @refresh="refresh()"
    />
    <custom-asset-table
      class="mt-12"
      :assets="state.data"
      :loading="loading"
      :server-item-length="state.found"
      :filters="filters"
      :matchers="matchers"
      :expanded="expanded"
      :options="options"
      @add="add()"
      @edit="edit($event)"
      @delete-asset="showDeleteConfirmation($event)"
      @update:pagination="setOptions($event)"
      @update:filters="setFilter($event)"
      @update:expanded="expanded = $event"
    />
    <custom-asset-form-dialog
      :title="dialogTitle"
      :types="types"
      :editable-item="editableItem"
    />
  </v-container>
</template>

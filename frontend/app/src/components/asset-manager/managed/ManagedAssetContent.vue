<script setup lang="ts">
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
const ignoredAssetsHandling = ref<IgnoredAssetsHandlingType>('exclude');
const showUserOwnedAssetsOnly = ref(false);

const extraParams = computed(() => ({
  ignoredAssetsHandling: get(ignoredAssetsHandling),
  showUserOwnedAssetsOnly: get(showUserOwnedAssetsOnly).toString()
}));

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

const deleteAssetHandler = async (identifier: string) => {
  try {
    const success = await deleteAsset(identifier);
    if (success) {
      await fetchData();
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

watch([ignoredAssetsHandling, showUserOwnedAssetsOnly], async () => {
  setPage(1);
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
    set(ignoredAssetsHandling, query.ignoredAssetsHandling || 'exclude');
    set(showUserOwnedAssetsOnly, query.showUserOwnedAssetsOnly === 'true');
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
  <VContainer>
    <RefreshHeader
      :title="t('asset_management.managed.title')"
      :loading="loading"
      @refresh="fetchData()"
    />

    <VRow class="mt-2" justify="space-between">
      <VCol cols="auto">
        <VTooltip open-delay="400" top>
          <template #activator="{ on, attrs }">
            <VBtn
              outlined
              color="primary"
              v-bind="attrs"
              v-on="on"
              @click="mergeTool = true"
            >
              <VIcon class="mr-2">mdi-merge</VIcon>
              <span>{{ t('asset_management.merge_assets') }}</span>
            </VBtn>
          </template>
          <span>{{ t('asset_management.merge_assets_tooltip') }}</span>
        </VTooltip>
      </VCol>
      <VCol cols="auto">
        <RestoreAssetDbButton dropdown />
      </VCol>
    </VRow>

    <MergeDialog v-model="mergeTool" />

    <ManagedAssetTable
      class="mt-12"
      :tokens="assets.data"
      :loading="loading"
      :change="!loading"
      :server-item-length="assets.found"
      :filters="filters"
      :matchers="matchers"
      :ignored-assets="ignoredAssets"
      :ignored-assets-handling="ignoredAssetsHandling"
      :only-show-owned="showUserOwnedAssetsOnly"
      :expanded="expanded"
      :selected="selected"
      :options="options"
      @refresh="fetchData()"
      @add="add()"
      @edit="edit($event)"
      @delete-asset="showDeleteConfirmation($event)"
      @update:pagination="setOptions($event)"
      @update:filters="setFilter($event)"
      @update:expanded="expanded = $event"
      @update:selected="selected = $event"
      @update:ignored-assets-handling="ignoredAssetsHandling = $event"
      @update:only-show-owned="showUserOwnedAssetsOnly = $event"
    />

    <ManagedAssetFormDialog
      :title="dialogTitle"
      :editable-item="editableItem"
    />
  </VContainer>
</template>

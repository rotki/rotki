<script setup lang="ts">
import { type SupportedAsset } from '@rotki/common/lib/data';
import ManagedAssetForm from '@/components/asset-manager/ManagedAssetForm.vue';
import { useAssetFilter } from '@/composables/filters/assets';
import { type Collection } from '@/types/collection';
import { type Nullable } from '@/types';
import {
  type AssetRequestPayload,
  EVM_TOKEN,
  type IgnoredAssetsHandlingType
} from '@/types/asset';
import { assert } from '@/utils/assertions';
import { type Filters, type Matcher } from '@/composables/filters/assets';

const props = withDefaults(
  defineProps<{
    identifier?: string | null;
    mainPage?: boolean;
  }>(),
  { identifier: null, mainPage: false }
);

const { identifier, mainPage } = toRefs(props);

const validForm = ref<boolean>(false);
const showForm = ref<boolean>(false);
const saving = ref<boolean>(false);
const mergeTool = ref<boolean>(false);
const form = ref<InstanceType<typeof ManagedAssetForm> | null>(null);
const ignoredAssetsHandling = ref<IgnoredAssetsHandlingType>('exclude');
const showUserOwnedAssetsOnly = ref(false);

const extraParams = computed(() => ({
  ignoredAssetsHandling: get(ignoredAssetsHandling),
  showUserOwnedAssetsOnly: get(showUserOwnedAssetsOnly).toString()
}));

const dialogTitle = computed<string>(() =>
  get(asset)
    ? tc('asset_management.edit_title')
    : tc('asset_management.add_title')
);

const router = useRouter();
const route = useRoute();
const { tc } = useI18n();
const { queryAllAssets, deleteEthereumToken, deleteAsset } =
  useAssetManagementApi();
const { setMessage } = useMessageStore();
const { show } = useConfirmStore();
const { ignoredAssets } = storeToRefs(useIgnoredAssetsStore());

const add = () => {
  set(asset, null);
  set(showForm, true);
};

const edit = (editAsset: SupportedAsset) => {
  set(asset, editAsset);
  set(showForm, true);
};

const editAsset = async (assetId: Nullable<string>) => {
  if (assetId) {
    const foundAsset = get(assets).data.find(
      ({ identifier: id }) => id === assetId
    );
    if (foundAsset) {
      edit(foundAsset);
    }
  }
};

const save = async () => {
  set(saving, true);
  const success = await get(form)?.save();
  if (success) {
    set(showForm, false);
    await fetchData();
    set(asset, null);
  }
  set(saving, false);
};

const deleteToken = async (address: string, chain: string) => {
  try {
    const success = await deleteEthereumToken(address, chain);
    if (success) {
      await fetchData();
    }
  } catch (e: any) {
    setMessage({
      description: tc('asset_management.delete_error', 0, {
        address,
        message: e.message
      })
    });
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
      description: tc('asset_management.delete_error', 0, {
        address: identifier,
        message: e.message
      })
    });
  }
};

const confirmDelete = async (toDeleteAsset: SupportedAsset) => {
  if (toDeleteAsset.type === EVM_TOKEN) {
    await deleteAssetHandler(toDeleteAsset.identifier);
  } else {
    const address = toDeleteAsset.address;
    assert(address);
    await deleteToken(address, toDeleteAsset.evmChain as string);
  }
};

const closeDialog = async () => {
  set(showForm, false);
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
  editableItem: asset,
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
    ascending: [false]
  }
});

const showDeleteConfirmation = (item: SupportedAsset) => {
  show(
    {
      title: tc('asset_management.confirm_delete.title'),
      message: tc('asset_management.confirm_delete.message', 0, {
        asset: item?.symbol ?? ''
      })
    },
    async () => await confirmDelete(item)
  );
};

onMounted(async () => {
  await editAsset(get(identifier));

  const query = get(route).query;
  if (query.add) {
    add();
    await router.replace({ query: {} });
  }
});

watch(identifier, async assetId => {
  await editAsset(assetId);
});
</script>

<template>
  <v-container>
    <refresh-header
      :title="tc('asset_management.managed.title')"
      :loading="loading"
      @refresh="fetchData"
    />

    <v-row class="mt-2" justify="space-between">
      <v-col cols="auto">
        <v-tooltip open-delay="400" top>
          <template #activator="{ on, attrs }">
            <v-btn
              outlined
              color="primary"
              v-bind="attrs"
              v-on="on"
              @click="mergeTool = true"
            >
              <v-icon class="mr-2">mdi-merge</v-icon>
              <span>{{ tc('asset_management.merge_assets') }}</span>
            </v-btn>
          </template>
          <span>{{ tc('asset_management.merge_assets_tooltip') }}</span>
        </v-tooltip>
      </v-col>
      <v-col cols="auto">
        <restore-asset-db-button dropdown />
      </v-col>
    </v-row>

    <merge-dialog v-model="mergeTool" />

    <managed-asset-table
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
      @refresh="fetchData"
      @add="add()"
      @edit="edit"
      @delete-asset="showDeleteConfirmation"
      @update:pagination="setOptions"
      @update:filters="setFilter"
      @update:expanded="expanded = $event"
      @update:selected="selected = $event"
      @update:ignored-assets-handling="ignoredAssetsHandling = $event"
      @update:only-show-owned="showUserOwnedAssetsOnly = $event"
    />
    <big-dialog
      :display="showForm"
      :title="dialogTitle"
      subtitle=""
      :action-disabled="!validForm || saving"
      :primary-action="tc('common.actions.save')"
      :loading="saving"
      @confirm="save()"
      @cancel="closeDialog()"
    >
      <managed-asset-form
        ref="form"
        :value="validForm"
        :edit="asset"
        :saving="saving"
      />
    </big-dialog>
  </v-container>
</template>

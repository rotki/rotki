<script setup lang="ts">
import CustomAssetForm from '@/components/asset-manager/CustomAssetForm.vue';
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
const valid = ref<boolean>(false);
const showForm = ref<boolean>(false);
const saving = ref<boolean>(false);
const editMode = ref<boolean>(false);
const assetForm = ref<InstanceType<typeof CustomAssetForm> | null>(null);

const dialogTitle = computed<string>(() =>
  get(editMode)
    ? tc('asset_management.edit_title')
    : tc('asset_management.add_title')
);

const router = useRouter();
const route = useRoute();
const { tc } = useI18n();
const { deleteCustomAsset, queryAllCustomAssets, getCustomAssetTypes } =
  useAssetManagementApi();
const { setMessage } = useMessageStore();

const { show } = useConfirmStore();

const add = () => {
  set(showForm, true);
  set(editMode, false);

  nextTick(() => {
    get(assetForm)?.setForm?.();
  });
};

const edit = (editAsset: CustomAsset) => {
  set(showForm, true);
  set(editMode, true);

  nextTick(() => {
    get(assetForm)?.setForm?.(editAsset);
  });
};

const save = async () => {
  set(saving, true);
  const assetId = await get(assetForm)?.save();

  if (assetId) {
    set(showForm, false);
    await refresh();
  }

  set(saving, false);
};

const deleteAsset = async (assetId: string) => {
  try {
    const success = await deleteCustomAsset(assetId);
    if (success) {
      await refresh();
    }
  } catch (e: any) {
    setMessage({
      description: tc('asset_management.delete_error', 0, {
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

const closeDialog = async () => {
  set(showForm, false);
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
const showDeleteConfirmation = (item: CustomAsset) => {
  show(
    {
      title: tc('asset_management.confirm_delete.title'),
      message: tc('asset_management.confirm_delete.message', 0, {
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
      :title="tc('asset_management.custom.title')"
      :loading="loading"
      @refresh="refresh"
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
      @edit="edit"
      @delete-asset="showDeleteConfirmation"
      @update:pagination="setOptions"
      @update:filters="setFilter"
      @update:expanded="expanded = $event"
    />
    <big-dialog
      :display="showForm"
      :title="dialogTitle"
      subtitle=""
      :action-disabled="!valid || saving"
      :primary-action="tc('common.actions.save')"
      :loading="saving"
      @confirm="save()"
      @cancel="closeDialog()"
    >
      <custom-asset-form
        ref="assetForm"
        :types="types"
        :edit="editMode"
        @valid="valid = $event"
      />
    </big-dialog>
  </v-container>
</template>

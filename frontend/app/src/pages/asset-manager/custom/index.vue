<script setup lang="ts">
import { type Ref } from 'vue';
import CustomAssetForm from '@/components/asset-manager/CustomAssetForm.vue';
import CustomAssetTable from '@/components/asset-manager/CustomAssetTable.vue';
import BigDialog from '@/components/dialogs/BigDialog.vue';
import { Routes } from '@/router/routes';
import { type Nullable } from '@/types';
import {
  type CustomAsset,
  type CustomAssetPagination,
  defaultCustomAssetPagination
} from '@/types/asset';
import { convertPagination } from '@/types/pagination';

const props = defineProps({
  identifier: { required: false, type: String, default: null }
});

const { identifier } = toRefs(props);

const { setMessage } = useMessageStore();
const { itemsPerPage } = storeToRefs(useFrontendSettingsStore());

const types = ref<string[]>([]);
const loading = ref<boolean>(false);
const assets = ref<CustomAsset[]>([]);
const valid = ref<boolean>(false);
const showForm = ref<boolean>(false);
const saving = ref<boolean>(false);
const totalEntries = ref(0);
const pagination: Ref<CustomAssetPagination> = ref(
  convertPagination(defaultCustomAssetPagination(get(itemsPerPage)), 'name')
);
const editMode = ref<boolean>(false);

const { tc } = useI18n();
const { deleteCustomAsset, queryAllCustomAssets, getCustomAssetTypes } =
  useAssetManagementApi();

const dialogTitle = computed<string>(() => {
  return get(editMode)
    ? tc('asset_management.edit_title')
    : tc('asset_management.add_title');
});

const assetForm: Ref<InstanceType<typeof CustomAssetForm> | null> = ref(null);

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
  const identifier = await get(assetForm)?.save();

  if (identifier) {
    set(showForm, false);
    await refresh();
  }

  set(saving, false);
};

const deleteAsset = async (identifier: string) => {
  try {
    const success = await deleteCustomAsset(identifier);
    if (success) {
      await refresh();
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

onMounted(async () => {
  await refresh();
});

watch(pagination, () => refresh());

const refresh = async () => {
  set(loading, true);
  const supportedAssets = await queryAllCustomAssets(get(pagination));
  set(assets, supportedAssets.entries);
  set(totalEntries, supportedAssets.entriesFound);
  set(types, await getCustomAssetTypes());
  set(loading, false);
};

const editAsset = (identifier: Nullable<string>) => {
  if (identifier) {
    const asset = get(assets).find(({ identifier: id }) => id === identifier);
    if (asset) {
      edit(asset);
    }
  }
};

const router = useRouter();
const route = useRoute();

const closeDialog = async () => {
  set(showForm, false);
  await router.push(Routes.ASSET_MANAGER_CUSTOM);
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

watch(identifier, identifier => {
  editAsset(identifier);
});

const { show } = useConfirmStore();

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
      :assets="assets"
      :loading="loading"
      :server-item-length="totalEntries"
      :types="types"
      @add="add()"
      @edit="edit($event)"
      @delete-asset="showDeleteConfirmation($event)"
      @update:pagination="pagination = $event"
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

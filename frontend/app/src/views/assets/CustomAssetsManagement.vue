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
      @delete-asset="toDeleteAsset = $event"
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
        v-model="formData"
        :types="types"
        :edit="editMode"
        @valid="valid = $event"
      />
    </big-dialog>
    <confirm-dialog
      :title="tc('asset_management.confirm_delete.title')"
      :message="
        tc('asset_management.confirm_delete.message', 0, deleteAssetSymbol)
      "
      :display="!!toDeleteAsset"
      @confirm="confirmDelete"
      @cancel="toDeleteAsset = null"
    />
  </v-container>
</template>

<script setup lang="ts">
import { omit } from 'lodash';
import { Ref } from 'vue';
import CustomAssetForm from '@/components/asset-manager/CustomAssetForm.vue';
import CustomAssetTable from '@/components/asset-manager/CustomAssetTable.vue';
import BigDialog from '@/components/dialogs/BigDialog.vue';
import { useRoute, useRouter } from '@/composables/router';
import { Routes } from '@/router/routes';
import { useAssetManagementApi } from '@/services/assets/management-api';
import { api } from '@/services/rotkehlchen-api';
import { useMessageStore } from '@/store/message';
import { useFrontendSettingsStore } from '@/store/settings/frontend';
import { Nullable } from '@/types';
import {
  CustomAsset,
  CustomAssetPagination,
  defaultCustomAssetPagination
} from '@/types/assets';
import { convertPagination } from '@/types/pagination';
import { assert } from '@/utils/assertions';

const props = defineProps({
  identifier: { required: false, type: String, default: null }
});

const emptyCustomAsset: () => CustomAsset = () => ({
  identifier: '',
  name: '',
  customAssetType: '',
  notes: ''
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
const toDeleteAsset = ref<Nullable<CustomAsset>>(null);
const totalEntries = ref(0);
const pagination: Ref<CustomAssetPagination> = ref(
  convertPagination(defaultCustomAssetPagination(get(itemsPerPage)), 'name')
);
const editMode = ref<boolean>(false);
const formData = ref<CustomAsset>(emptyCustomAsset());

const { tc } = useI18n();

const deleteAssetSymbol = computed(() => ({
  asset: get(toDeleteAsset)?.name ?? ''
}));

const dialogTitle = computed<string>(() => {
  return get(editMode)
    ? tc('asset_management.edit_title')
    : tc('asset_management.add_title');
});

const { queryAllCustomAssets } = useAssetManagementApi();

const add = () => {
  set(editMode, false);
  set(formData, emptyCustomAsset());
  set(showForm, true);
};

const edit = (editAsset: CustomAsset) => {
  set(editMode, true);
  set(formData, editAsset);
  set(showForm, true);
};

const save = async () => {
  set(saving, true);
  const form = get(formData);
  let success: boolean = false;
  try {
    if (get(editMode)) {
      success = await api.assets.editCustomAsset(form);
    } else {
      const identifier = await api.assets.addCustomAsset(
        omit(form, 'identifier')
      );
      success = !!identifier;
    }
  } catch (e: any) {
    const obj = { message: e.message };
    setMessage({
      description: get(editMode)
        ? tc('asset_management.edit_error', 0, obj)
        : tc('asset_management.add_error', 0, obj)
    });
  } finally {
    if (success) {
      set(showForm, false);
      await refresh();
    }
    set(saving, false);
  }
};

const deleteAsset = async (identifier: string) => {
  try {
    const success = await api.assets.deleteCustomAsset(identifier);
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

const confirmDelete = async () => {
  const asset = get(toDeleteAsset);
  set(toDeleteAsset, null);
  assert(asset);
  await deleteAsset(asset.identifier);
};

onMounted(async () => {
  await refresh();
});

watch(pagination, () => refresh());

const refresh = async () => {
  let supportedAssets = await queryAllCustomAssets(get(pagination));
  set(assets, supportedAssets.entries);
  set(totalEntries, supportedAssets.entriesFound);
  set(types, await api.assets.getCustomAssetTypes());
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
</script>

<template>
  <v-container>
    <refresh-header
      :title="tc('asset_management.managed.title')"
      :loading="loading"
      @refresh="refresh"
    />

    <v-row class="mt-2" justify="space-between">
      <v-col cols="auto">
        <ignore-scam-assets-button @refresh="refresh" />
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
        <restore-asset-db-button />
      </v-col>
    </v-row>

    <merge-dialog v-model="mergeTool" />

    <managed-asset-table
      class="mt-12"
      :tokens="assets"
      :loading="loading"
      :change="!loading"
      :server-item-length="totalEntries"
      @add="add()"
      @edit="edit($event)"
      @delete-asset="toDeleteAsset = $event"
      @update:pagination="pagination = $event"
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
        v-model="validForm"
        :edit="asset"
        :saving="saving"
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
import { SupportedAsset } from '@rotki/common/lib/data';
import { Ref } from 'vue';
import IgnoreScamAssetsButton from '@/components/asset-manager/IgnoreScamAssetsButton.vue';
import ManagedAssetForm from '@/components/asset-manager/ManagedAssetForm.vue';
import ManagedAssetTable from '@/components/asset-manager/ManagedAssetTable.vue';
import MergeDialog from '@/components/asset-manager/MergeDialog.vue';
import RestoreAssetDbButton from '@/components/asset-manager/RestoreAssetDbButton.vue';
import BigDialog from '@/components/dialogs/BigDialog.vue';
import ConfirmDialog from '@/components/dialogs/ConfirmDialog.vue';
import { useRoute, useRouter } from '@/composables/router';
import { Routes } from '@/router/routes';
import { EVM_TOKEN } from '@/services/assets/consts';
import { useAssetManagementApi } from '@/services/assets/management-api';
import { api } from '@/services/rotkehlchen-api';
import { useMessageStore } from '@/store/message';
import { useFrontendSettingsStore } from '@/store/settings/frontend';
import { Nullable } from '@/types';
import { AssetPagination, defaultAssetPagination } from '@/types/assets';
import { convertPagination } from '@/types/pagination';
import { assert } from '@/utils/assertions';

const props = defineProps({
  identifier: { required: false, type: String, default: null }
});

const { identifier } = toRefs(props);
const { setMessage } = useMessageStore();
const { itemsPerPage } = storeToRefs(useFrontendSettingsStore());

const loading = ref<boolean>(false);
const assets = ref<SupportedAsset[]>([]);
const validForm = ref<boolean>(false);
const showForm = ref<boolean>(false);
const saving = ref<boolean>(false);
const asset = ref<Nullable<SupportedAsset>>(null);
const toDeleteAsset = ref<Nullable<SupportedAsset>>(null);
const mergeTool = ref<boolean>(false);
const form = ref<any>(null);
const totalEntries = ref(0);
const pagination: Ref<AssetPagination> = ref(
  convertPagination(defaultAssetPagination(get(itemsPerPage)), 'symbol')
);

const { tc } = useI18n();

const deleteAssetSymbol = computed(() => ({
  asset: get(toDeleteAsset)?.symbol ?? ''
}));

const dialogTitle = computed<string>(() => {
  return get(asset)
    ? tc('asset_management.edit_title')
    : tc('asset_management.add_title');
});

const { queryAllAssets } = useAssetManagementApi();

const add = () => {
  set(asset, null);
  set(showForm, true);
};

const edit = (editAsset: SupportedAsset) => {
  set(asset, editAsset);
  set(showForm, true);
};

const editAsset = async (identifier: Nullable<string>) => {
  if (identifier) {
    const result = await queryAllAssets({
      identifiers: [identifier]
    });
    if (result?.entries?.length > 0) {
      edit(result.entries[0]);
    }
  }
};

const save = async () => {
  set(saving, true);
  const success = await get(form)?.save();
  if (success) {
    set(showForm, false);
    await refresh();
    set(asset, null);
  }
  set(saving, false);
};

const deleteToken = async (address: string, chain: string) => {
  try {
    const success = await api.assets.deleteEthereumToken(address, chain);
    if (success) {
      await refresh();
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

const deleteAsset = async (identifier: string) => {
  try {
    const success = await api.assets.deleteAsset(identifier);
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
  if (asset.type === EVM_TOKEN) {
    await deleteAsset(asset.identifier);
  } else {
    let address = asset.address;
    assert(address);
    await deleteToken(address, asset.chain as string);
  }
};

const router = useRouter();
const route = useRoute();

const closeDialog = async () => {
  set(showForm, false);
  await router.push(Routes.ASSET_MANAGER);
};

onMounted(async () => {
  await refresh();
  await editAsset(get(identifier));

  const query = get(route).query;
  if (query.add) {
    add();
    await router.replace({ query: {} });
  }
});

watch(identifier, async identifier => {
  await editAsset(identifier);
});

watch(pagination, () => refresh());

const refresh = async () => {
  let supportedAssets = await queryAllAssets(get(pagination));
  set(assets, supportedAssets.entries);
  set(totalEntries, supportedAssets.entriesFound);
};
</script>

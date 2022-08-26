<template>
  <v-container>
    <refresh-header
      :title="tc('asset_management.title')"
      :loading="loading"
      @refresh="refresh"
    />

    <v-row class="mt-2" justify="space-between">
      <v-col cols="auto">
        <v-btn
          class="mr-4 mb-sm-0 mb-4"
          color="primary"
          depressed
          :loading="isUpdateIgnoredAssetsLoading"
          :disabled="isUpdateIgnoredAssetsLoading"
          @click="updateIgnoredAssets"
        >
          <v-icon class="mr-2">mdi-sync</v-icon>
          {{ tc('asset_management.sync_ignored_assets_list') }}
          <v-chip
            small
            class="ml-2 px-2 asset_management__ignored-assets__chip"
            color="white"
            text-color="primary"
          >
            {{ ignoredAssets.length }}
          </v-chip>
        </v-btn>
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

    <asset-table
      class="mt-12"
      :tokens="tokens"
      :loading="loading"
      :change="!loading"
      @add="add()"
      @edit="edit($event)"
      @delete-asset="toDeleteAsset = $event"
    />
    <big-dialog
      :display="showForm"
      :title="dialogTitle"
      subtitle=""
      :action-disabled="!validForm || saving"
      :primary-action="'save'"
      :loading="saving"
      @confirm="save()"
      @cancel="closeDialog()"
    >
      <asset-form
        v-if="token"
        ref="form"
        v-model="validForm"
        :edit="token"
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
import { get, set } from '@vueuse/core';
import { storeToRefs } from 'pinia';
import { computed, onMounted, ref, toRefs, watch } from 'vue';
import { useI18n } from 'vue-i18n-composable';
import AssetForm from '@/components/asset-manager/AssetForm.vue';
import AssetTable from '@/components/asset-manager/AssetTable.vue';
import MergeDialog from '@/components/asset-manager/MergeDialog.vue';
import RestoreAssetDbButton from '@/components/asset-manager/RestoreAssetDbButton.vue';
import BigDialog from '@/components/dialogs/BigDialog.vue';
import ConfirmDialog from '@/components/dialogs/ConfirmDialog.vue';
import { useRoute, useRouter } from '@/composables/common';
import { Routes } from '@/router/routes';
import { EVM_TOKEN } from '@/services/assets/consts';
import { ManagedAsset } from '@/services/assets/types';
import { api } from '@/services/rotkehlchen-api';
import { useAssetInfoRetrieval, useIgnoredAssetsStore } from '@/store/assets';
import { useTasks } from '@/store/tasks';
import { showError } from '@/store/utils';
import { Nullable } from '@/types';
import { TaskType } from '@/types/task-type';
import { assert } from '@/utils/assertions';

const props = defineProps({
  identifier: { required: false, type: String, default: null }
});

const { identifier } = toRefs(props);

const assetsStore = useAssetInfoRetrieval();
const { supportedAssets } = storeToRefs(assetsStore);
const { fetchSupportedAssets } = assetsStore;

const loading = ref<boolean>(false);
const tokens = ref<ManagedAsset[]>([]);
const validForm = ref<boolean>(false);
const showForm = ref<boolean>(false);
const saving = ref<boolean>(false);
const token = ref<Nullable<ManagedAsset>>(null);
const toDeleteAsset = ref<Nullable<ManagedAsset>>(null);
const mergeTool = ref<boolean>(false);
const form = ref<any>(null);

const { tc } = useI18n();

const deleteAssetSymbol = computed(() => ({
  asset: get(toDeleteAsset)?.symbol ?? ''
}));

const dialogTitle = computed<string>(() => {
  return get(token)
    ? tc('asset_management.edit_title')
    : tc('asset_management.add_title');
});

const add = () => {
  set(token, null);
  set(showForm, true);
};

const edit = (tokenToEdit: ManagedAsset) => {
  set(token, tokenToEdit);
  set(showForm, true);
};

const editAsset = (identifier: Nullable<string>) => {
  if (identifier) {
    const token = get(tokens).find(({ identifier: id }) => id === identifier);
    if (token) {
      edit(token);
    }
  }
};

const refresh = async () => {
  set(loading, true);
  await fetchSupportedAssets(true);
  const assets = get(supportedAssets).filter(
    ({ assetType }) => assetType !== EVM_TOKEN
  );
  set(tokens, [...(await api.assets.ethereumTokens()), ...assets]);
  set(loading, false);
};

const save = async () => {
  set(saving, true);
  const success = await get(form)?.save();
  if (success) {
    set(showForm, false);
    await refresh();
    set(token, null);
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
    showError(
      tc('asset_management.delete_error', 0, {
        address,
        message: e.message
      })
    );
  }
};

const deleteAsset = async (identifier: string) => {
  try {
    const success = await api.assets.deleteAsset(identifier);
    if (success) {
      await refresh();
    }
  } catch (e: any) {
    showError(
      tc('asset_management.delete_error', 0, {
        address: identifier,
        message: e.message
      })
    );
  }
};

const confirmDelete = async () => {
  const asset = get(toDeleteAsset);
  set(toDeleteAsset, null);
  assert(asset !== null);
  if ('assetType' in asset) {
    await deleteAsset(asset.identifier);
  } else {
    await deleteToken(asset.address, asset.chain as string);
  }
};

const router = useRouter();
const route = useRoute();

const closeDialog = async () => {
  set(showForm, false);
  router.push(Routes.ASSET_MANAGER.route);
};

onMounted(async () => {
  await refresh();
  editAsset(get(identifier));

  const query = get(route).query;
  if (query.add) {
    add();
    router.replace({ query: {} });
  }
});

watch(identifier, identifier => {
  editAsset(identifier);
});

const ignoredAssetsStore = useIgnoredAssetsStore();
const { ignoredAssets } = storeToRefs(ignoredAssetsStore);
const { updateIgnoredAssets } = ignoredAssetsStore;

const { isTaskRunning } = useTasks();
const isUpdateIgnoredAssetsLoading = isTaskRunning(
  TaskType.UPDATE_IGNORED_ASSETS
);
</script>

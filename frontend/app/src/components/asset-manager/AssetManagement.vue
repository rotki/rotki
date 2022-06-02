<template>
  <v-container>
    <refresh-header
      :title="$tc('asset_management.title')"
      :loading="loading"
      @refresh="refresh"
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
              <v-icon>mdi-merge</v-icon>
              <span>{{ $t('asset_management.merge_assets') }}</span>
            </v-btn>
          </template>
          <span>{{ $t('asset_management.merge_assets_tooltip') }}</span>
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
        ref="form"
        v-model="validForm"
        :edit="token"
        :saving="saving"
      />
    </big-dialog>
    <confirm-dialog
      :title="$tc('asset_management.confirm_delete.title')"
      :message="
        $tc('asset_management.confirm_delete.message', {
          asset: deleteAssetSymbol
        })
      "
      :display="!!toDeleteAsset"
      @confirm="confirmDelete"
      @cancel="toDeleteAsset = null"
    />
  </v-container>
</template>

<script lang="ts">
import {
  computed,
  defineComponent,
  onMounted,
  ref,
  toRefs,
  watch
} from '@vue/composition-api';
import { get, set } from '@vueuse/core';
import AssetForm from '@/components/asset-manager/AssetForm.vue';
import AssetTable from '@/components/asset-manager/AssetTable.vue';
import MergeDialog from '@/components/asset-manager/MergeDialog.vue';
import RestoreAssetDbButton from '@/components/asset-manager/RestoreAssetDbButton.vue';
import BigDialog from '@/components/dialogs/BigDialog.vue';
import ConfirmDialog from '@/components/dialogs/ConfirmDialog.vue';
import { useRoute, useRouter } from '@/composables/common';
import i18n from '@/i18n';
import { Routes } from '@/router/routes';
import { ManagedAsset } from '@/services/assets/types';
import { api } from '@/services/rotkehlchen-api';
import { useAssetInfoRetrieval } from '@/store/assets';
import { showError } from '@/store/utils';
import { Nullable } from '@/types';
import { assert } from '@/utils/assertions';

export default defineComponent({
  name: 'AssetManagement',
  components: {
    RestoreAssetDbButton,
    MergeDialog,
    ConfirmDialog,
    AssetForm,
    BigDialog,
    AssetTable
  },
  props: {
    identifier: { required: false, type: String, default: null }
  },
  setup(props) {
    const { identifier } = toRefs(props);

    const { supportedAssets, fetchSupportedAssets } = useAssetInfoRetrieval();

    const loading = ref<boolean>(false);
    const tokens = ref<ManagedAsset[]>([]);
    const validForm = ref<boolean>(false);
    const showForm = ref<boolean>(false);
    const saving = ref<boolean>(false);
    const token = ref<Nullable<ManagedAsset>>(null);
    const toDeleteAsset = ref<Nullable<ManagedAsset>>(null);
    const mergeTool = ref<boolean>(false);
    const restoreMode = ref<string>('soft');
    const form = ref<any>(null);

    const deleteAssetSymbol = computed<string>(() => {
      return get(toDeleteAsset)?.symbol ?? '';
    });

    const dialogTitle = computed<string>(() => {
      return get(token)
        ? i18n.t('asset_management.edit_title').toString()
        : i18n.t('asset_management.add_title').toString();
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
        const token = get(tokens).find(
          ({ identifier: id }) => id === identifier
        );
        if (token) {
          edit(token);
        }
      }
    };

    const refresh = async () => {
      set(loading, true);
      await fetchSupportedAssets(true);
      const assets = get(supportedAssets).filter(
        ({ assetType }) => assetType !== 'ethereum token'
      );
      set(tokens, [...(await api.assets.ethereumTokens()), ...assets]);
      set(loading, false);
    };

    const save = async () => {
      set(saving, true);
      const success = await get(form)?.save();
      if (success) {
        set(showForm, false);
        refresh();
        set(token, null);
      }
      set(saving, false);
    };

    const deleteToken = async (address: string) => {
      try {
        const success = await api.assets.deleteEthereumToken(address);
        if (success) {
          await refresh();
        }
      } catch (e: any) {
        showError(
          i18n
            .t('asset_management.delete_error', {
              address,
              message: e.message
            })
            .toString()
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
          i18n
            .t('asset_management.delete_error', {
              address: identifier,
              message: e.message
            })
            .toString()
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
        await deleteToken(asset.address);
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

    return {
      loading,
      refresh,
      tokens,
      validForm,
      showForm,
      saving,
      token,
      toDeleteAsset,
      mergeTool,
      restoreMode,
      form,
      add,
      edit,
      dialogTitle,
      save,
      closeDialog,
      deleteAssetSymbol,
      confirmDelete
    };
  }
});
</script>

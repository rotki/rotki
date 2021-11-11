<template>
  <v-container>
    <refresh-header
      :title="$t('asset_management.title')"
      :loading="loading"
      @refresh="refresh"
    />

    <v-row class="mt-2" justify="space-between">
      <v-col md="3">
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
      <v-col md="2">
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
      :title="$t('asset_management.confirm_delete.title')"
      :message="
        $t('asset_management.confirm_delete.message', {
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
import { SupportedAsset } from '@rotki/common/lib/data';
import { Component, Prop, Vue, Watch } from 'vue-property-decorator';
import { mapActions, mapState } from 'vuex';
import AssetForm from '@/components/asset-manager/AssetForm.vue';
import AssetTable from '@/components/asset-manager/AssetTable.vue';
import MergeDialog from '@/components/asset-manager/MergeDialog.vue';
import RestoreAssetDbButton from '@/components/asset-manager/RestoreAssetDbButton.vue';
import BigDialog from '@/components/dialogs/BigDialog.vue';
import ConfirmDialog from '@/components/dialogs/ConfirmDialog.vue';
import { Routes } from '@/router/routes';
import { ManagedAsset } from '@/services/assets/types';
import { showError } from '@/store/utils';
import { Nullable } from '@/types';
import { assert } from '@/utils/assertions';

@Component({
  components: {
    RestoreAssetDbButton,
    MergeDialog,
    ConfirmDialog,
    AssetForm,
    BigDialog,
    AssetTable
  },
  computed: {
    ...mapState('balances', ['supportedAssets'])
  },
  methods: {
    ...mapActions('session', ['logout'])
  }
})
export default class AssetManagement extends Vue {
  @Prop({
    type: String,
    required: false,
    default: null
  })
  identifier!: Nullable<string>;

  @Watch('identifier')
  onIdentifierChange(value: Nullable<string>) {
    this.editAsset(value);
  }

  loading: boolean = false;
  tokens: ManagedAsset[] = [];
  validForm: boolean = false;
  showForm: boolean = false;
  saving: boolean = false;
  token: Nullable<ManagedAsset> = null;
  supportedAssets!: SupportedAsset[];
  toDeleteAsset: Nullable<ManagedAsset> = null;
  mergeTool: boolean = false;
  logout!: () => Promise<void>;
  restoreMode: string = 'soft';

  get deleteAssetSymbol(): string {
    return this.toDeleteAsset?.symbol ?? '';
  }

  get dialogTitle(): string {
    return this.token
      ? this.$t('asset_management.edit_title').toString()
      : this.$t('asset_management.add_title').toString();
  }

  async mounted() {
    await this.refresh();
    const identifier = this.identifier;
    this.editAsset(identifier);
  }

  private editAsset(identifier: string | null) {
    if (identifier) {
      const token = this.tokens.find(({ identifier: id }) => id === identifier);
      if (token) {
        this.edit(token);
      }
    }
  }

  private async refresh() {
    this.loading = true;
    await this.$store.dispatch('balances/fetchSupportedAssets', true);
    const assets = this.supportedAssets.filter(
      ({ assetType }) => assetType !== 'ethereum token'
    );
    this.tokens = [...(await this.$api.assets.ethereumTokens()), ...assets];
    this.loading = false;
  }

  add() {
    this.token = null;
    this.showForm = true;
  }

  edit(token: ManagedAsset) {
    this.token = token;
    this.showForm = true;
  }

  async save() {
    this.saving = true;
    const success = await (this.$refs.form as any).save();
    if (success) {
      this.showForm = false;
      await this.refresh();
      this.token = null;
    }
    this.saving = false;
  }

  async confirmDelete() {
    const asset = this.toDeleteAsset;
    this.toDeleteAsset = null;
    assert(asset !== null);
    if ('assetType' in asset) {
      await this.deleteAsset(asset.identifier);
    } else {
      await this.deleteToken(asset.address);
    }
  }

  async deleteToken(address: string) {
    try {
      const success = await this.$api.assets.deleteEthereumToken(address);
      if (success) {
        await this.refresh();
      }
    } catch (e: any) {
      showError(
        this.$t('asset_management.delete_error', {
          address,
          message: e.message
        }).toString()
      );
    }
  }

  async deleteAsset(identifier: string) {
    try {
      const success = await this.$api.assets.deleteAsset(identifier);
      if (success) {
        await this.refresh();
      }
    } catch (e: any) {
      showError(
        this.$t('asset_management.delete_error', {
          address: identifier,
          message: e.message
        }).toString()
      );
    }
  }

  async closeDialog() {
    this.showForm = false;
    await this.$router.push(Routes.ASSET_MANAGER);
  }
}
</script>

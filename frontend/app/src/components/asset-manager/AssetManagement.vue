<template>
  <v-container>
    <refresh-header
      class="mt-8"
      :title="$t('asset_management.title')"
      :loading="loading"
      @refresh="refresh"
    />
    <asset-table
      class="mt-12"
      :tokens="tokens"
      :loading="loading"
      :change="!loading"
      @add="add()"
      @edit="edit($event)"
      @delete-token="deleteToken($event)"
    />
    <big-dialog
      :display="showForm"
      :title="dialogTitle"
      :subtitle="dialogSubtitle"
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
  </v-container>
</template>

<script lang="ts">
import { Component, Vue } from 'vue-property-decorator';
import AssetForm from '@/components/asset-manager/AssetForm.vue';
import AssetTable from '@/components/asset-manager/AssetTable.vue';
import BigDialog from '@/components/dialogs/BigDialog.vue';
import { CustomEthereumToken } from '@/services/assets/types';

@Component({
  components: { AssetForm, BigDialog, AssetTable }
})
export default class AssetManagement extends Vue {
  loading: boolean = false;
  tokens: CustomEthereumToken[] = [];
  validForm: boolean = false;
  showForm: boolean = false;
  saving: boolean = false;
  token: CustomEthereumToken | null = null;

  get dialogTitle(): string {
    return this.token
      ? this.$t('asset_management.edit_title').toString()
      : this.$t('asset_management.add_title').toString();
  }

  get dialogSubtitle(): string {
    return '';
  }

  async mounted() {
    await this.refresh();
  }

  private async refresh() {
    this.loading = true;
    this.tokens = await this.$api.assets.customTokens();
    this.loading = false;
  }

  add() {
    this.token = null;
    this.showForm = true;
  }

  edit(token: CustomEthereumToken) {
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

  async deleteToken(address: string) {
    const success = await this.$api.assets.deleteCustomToken(address);
    if (success) {
      await this.refresh();
    }
  }

  async closeDialog() {
    this.showForm = false;
  }
}
</script>

<style scoped lang="scss"></style>

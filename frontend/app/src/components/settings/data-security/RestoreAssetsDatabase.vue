<template>
  <fragment>
    <card class="mt-8">
      <template #title>{{ $t('asset_update.restore.title') }}</template>
      <template #subtitle>{{ $t('asset_update.restore.subtitle') }}</template>
      <v-btn
        depressed
        color="primary"
        class="mt-2"
        @click="activateRestoreAssets()"
      >
        {{ $t('asset_update.restore.action') }}
      </v-btn>
    </card>
    <confirm-dialog
      :display="confirmRestore"
      :title="$t('asset_update.restore.delete_confirmation.title')"
      :message="$t('asset_update.restore.delete_confirmation.message')"
      @confirm="restoreAssets"
      @cancel="confirmRestore = false"
    />
  </fragment>
</template>

<script lang="ts">
import { Component, Vue } from 'vue-property-decorator';
import ConfirmDialog from '@/components/dialogs/ConfirmDialog.vue';
import Fragment from '@/components/helper/Fragment';
import { Severity } from '@/store/notifications/consts';
import { notify } from '@/store/notifications/utils';

@Component({
  components: {
    ConfirmDialog,
    Fragment
  }
})
export default class RestoreAssetsDatabase extends Vue {
  confirmRestore: boolean = false;
  done: boolean = false;

  activateRestoreAssets() {
    this.confirmRestore = true;
  }

  async restoreAssets() {
    try {
      this.confirmRestore = false;
      let updated = await this.$api.assets.restoreAssetsDatabase();
      if (updated) {
        const title = this.$t('asset_update.restore.success.title').toString();
        const description = this.$t(
          'asset_update.restore.success.description'
        ).toString();
        this.done = true;
        notify(description, title, Severity.INFO, true);
      }
    } catch (e) {
      const title = this.$t('asset_update.restore.title').toString();
      const message = this.$t('asset_update.restore.restore_error').toString();
      notify(message, title, Severity.ERROR, true);
    }
  }
}
</script>

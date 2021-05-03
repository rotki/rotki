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
    <confirm-dialog
      v-if="done"
      single-action
      display
      :title="$t('asset_update.restore.success.title')"
      :primary-action="$t('asset_update.success.ok')"
      :message="$t('asset_update.restore.success.description')"
      @confirm="updateComplete()"
    />
  </fragment>
</template>

<script lang="ts">
import { Component, Vue } from 'vue-property-decorator';
import { mapActions } from 'vuex';
import ConfirmDialog from '@/components/dialogs/ConfirmDialog.vue';
import Fragment from '@/components/helper/Fragment';
import { Severity } from '@/store/notifications/consts';
import { notify } from '@/store/notifications/utils';
import { currentLogLevel } from '@/utils/log-level';

@Component({
  components: {
    ConfirmDialog,
    Fragment
  },
  methods: {
    ...mapActions('session', ['logout'])
  }
})
export default class RestoreAssetsDatabase extends Vue {
  confirmRestore: boolean = false;
  done: boolean = false;
  logout!: () => Promise<void>;

  activateRestoreAssets() {
    this.confirmRestore = true;
  }

  async restoreAssets() {
    try {
      this.confirmRestore = false;
      let updated = await this.$api.assets.restoreAssetsDatabase();
      if (updated) {
        this.done = true;
      }
    } catch (e) {
      const title = this.$t('asset_update.restore.title').toString();
      const message = this.$t('asset_update.restore.restore_error').toString();
      notify(message, title, Severity.ERROR, true);
    }
  }

  async updateComplete() {
    await this.logout();
    if (this.$interop.isPackaged) {
      await this.$interop.restartBackend(currentLogLevel());
    }
  }
}
</script>

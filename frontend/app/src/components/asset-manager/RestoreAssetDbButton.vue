<template>
  <div>
    <v-btn depressed color="primary" @click="activateRestoreAssets()">
      {{ $t('asset_update.restore.action') }}
    </v-btn>
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
  </div>
</template>

<script lang="ts">
import { defineComponent } from '@vue/composition-api';
import RestoreAssetsDatabaseMixin from '@/mixins/restore-assets-database-mixin';

export default defineComponent({
  name: 'RestoreAssetDbButton',
  mixins: [RestoreAssetsDatabaseMixin]
});
</script>

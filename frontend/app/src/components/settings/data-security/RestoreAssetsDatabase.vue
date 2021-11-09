<template>
  <fragment>
    <card class="mt-8">
      <template #title>{{ $t('asset_update.restore.title') }}</template>
      <template #subtitle>{{ $t('asset_update.restore.subtitle') }}</template>
      <template #buttons>
        <v-btn
          depressed
          color="primary"
          class="mt-2"
          @click="activateRestoreAssets()"
        >
          {{ $t('asset_update.restore.action') }}
        </v-btn>
      </template>
    </card>
    <confirm-dialog
      :display="confirmRestore"
      :title="$t('asset_update.restore.hard_restore_message.title')"
      :message="$t('asset_update.restore.hard_restore_message.message')"
      @confirm="restoreAssets"
      @cancel="confirmRestore = false"
    />
    <confirm-dialog
      :display="doubleConfirmation"
      :title="$t('asset_update.restore.hard_restore_confirmation.title')"
      :message="$t('asset_update.restore.hard_restore_confirmation.message')"
      @confirm="confirmHardReset"
      @cancel="doubleConfirmation = false"
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
import { defineComponent } from '@vue/composition-api';
import Fragment from '@/components/helper/Fragment';
import RestoreAssetsDatabaseMixin from '@/mixins/restore-assets-database-mixin';

export default defineComponent({
  name: 'RestoreAssetsDatabase',
  components: { Fragment },
  mixins: [RestoreAssetsDatabaseMixin]
});
</script>

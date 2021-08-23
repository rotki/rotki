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
import { Component, Mixins } from 'vue-property-decorator';
import Fragment from '@/components/helper/Fragment';
import RestoreAssetsDatabase from '@/mixins/restoreAssets-mixin';

@Component({
  components: { Fragment }
})
export default class RestoreAssets extends Mixins(RestoreAssetsDatabase) {}
</script>

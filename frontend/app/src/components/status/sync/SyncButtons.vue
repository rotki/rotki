<template>
  <fragment>
    <v-tooltip top open-delay="400">
      <template #activator="{ on, attrs }">
        <v-btn
          v-bind="attrs"
          outlined
          depressed
          color="primary"
          :disabled="!premium || pending"
          v-on="on"
          @click="action(UPLOAD)"
        >
          <v-icon>mdi-cloud-upload</v-icon>
          <span class="ml-2">{{ $t('sync_buttons.push') }}</span>
        </v-btn>
      </template>
      <span>{{ $t('sync_buttons.upload_tooltip') }}</span>
    </v-tooltip>

    <v-tooltip top open-delay="400">
      <template #activator="{ on, attrs }">
        <v-btn
          v-bind="attrs"
          outlined
          depressed
          class="ml-2"
          color="primary"
          :disabled="!premium || pending"
          v-on="on"
          @click="action(DOWNLOAD)"
        >
          <v-icon>mdi-cloud-download</v-icon>
          <span class="ml-2">{{ $t('sync_buttons.pull') }}</span>
        </v-btn>
      </template>
      <span>{{ $t('sync_buttons.download_tooltip') }}</span>
    </v-tooltip>
  </fragment>
</template>

<script lang="ts">
import { Component, Emit, Mixins, Prop } from 'vue-property-decorator';
import Fragment from '@/components/helper/Fragment';
import PremiumMixin from '@/mixins/premium-mixin';
import { SYNC_DOWNLOAD, SYNC_UPLOAD, SyncAction } from '@/services/types-api';

@Component({
  components: { Fragment }
})
export default class SyncButtons extends Mixins(PremiumMixin) {
  @Prop({ required: true, type: Boolean })
  pending!: boolean;
  @Emit()
  action(_action: SyncAction) {}

  readonly UPLOAD = SYNC_UPLOAD;
  readonly DOWNLOAD = SYNC_DOWNLOAD;
}
</script>

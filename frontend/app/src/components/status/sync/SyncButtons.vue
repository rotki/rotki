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
import { defineComponent } from '@vue/composition-api';
import Fragment from '@/components/helper/Fragment';
import { getPremium } from '@/composables/session';
import { SYNC_DOWNLOAD, SYNC_UPLOAD, SyncAction } from '@/services/types-api';

export default defineComponent({
  name: 'SyncButtons',
  components: { Fragment },
  props: {
    pending: { required: true, type: Boolean }
  },
  emits: ['action'],
  setup(_, { emit }) {
    const premium = getPremium();

    const UPLOAD = SYNC_UPLOAD;
    const DOWNLOAD = SYNC_DOWNLOAD;

    const action = (_action: SyncAction) => {
      emit('action', _action);
    };

    return {
      premium,
      UPLOAD,
      DOWNLOAD,
      action
    };
  }
});
</script>

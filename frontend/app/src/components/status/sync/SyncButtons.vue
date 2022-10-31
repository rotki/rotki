<template>
  <div class="d-flex flex-wrap mx-n1">
    <v-tooltip top open-delay="400">
      <template #activator="{ on, attrs }">
        <v-btn
          v-bind="attrs"
          outlined
          depressed
          class="ma-1"
          color="primary"
          :disabled="!premium || pending"
          v-on="on"
          @click="action(UPLOAD)"
        >
          <v-icon>mdi-cloud-upload</v-icon>
          <span class="ml-2">{{ tc('common.actions.push') }}</span>
        </v-btn>
      </template>
      <span>{{ tc('sync_buttons.upload_tooltip') }}</span>
    </v-tooltip>

    <v-tooltip top open-delay="400">
      <template #activator="{ on, attrs }">
        <v-btn
          v-bind="attrs"
          outlined
          depressed
          class="ma-1"
          color="primary"
          :disabled="!premium || pending"
          v-on="on"
          @click="action(DOWNLOAD)"
        >
          <v-icon>mdi-cloud-download</v-icon>
          <span class="ml-2">{{ tc('common.actions.pull') }}</span>
        </v-btn>
      </template>
      <span>{{ tc('sync_buttons.download_tooltip') }}</span>
    </v-tooltip>
  </div>
</template>

<script setup lang="ts">
import { SYNC_DOWNLOAD, SYNC_UPLOAD, SyncAction } from '@/services/types-api';
import { usePremiumStore } from '@/store/session/premium';

defineProps({
  pending: { required: true, type: Boolean }
});

const emit = defineEmits<{
  (event: 'action', action: SyncAction): void;
}>();

const { tc } = useI18n();

const { premium } = storeToRefs(usePremiumStore());
const UPLOAD: SyncAction = SYNC_UPLOAD;
const DOWNLOAD: SyncAction = SYNC_DOWNLOAD;

const action = (action: SyncAction) => {
  emit('action', action);
};
</script>

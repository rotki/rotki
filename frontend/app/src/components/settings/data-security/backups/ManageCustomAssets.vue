<template>
  <card>
    <template #title>{{ t('manage_user_assets.title') }}</template>

    <v-alert type="info" outlined dense>
      {{ t('manage_user_assets.warning') }}
    </v-alert>

    <v-sheet outlined class="pa-4" rounded>
      <div class="text-h6">{{ t('manage_user_assets.export.title') }}</div>
      <div class="text-subtitle-1">
        {{ t('manage_user_assets.export.subtitle') }}
      </div>
      <v-alert v-if="exportError" type="error" outlined dense>
        {{ exportError }}
      </v-alert>
      <div class="d-flex flex-row align-center mt-4">
        <v-btn color="primary" :loading="downloading" @click="exportZip">
          {{ t('manage_user_assets.export.button') }}
        </v-btn>
        <v-icon v-if="downloaded" class="ms-4" color="success">
          mdi-check-circle
        </v-icon>
        <span v-if="downloaded" class="ms-2">
          {{ t('manage_user_assets.export.success') }}
        </span>
      </div>
    </v-sheet>

    <v-sheet outlined class="pa-4 mt-4" rounded>
      <div class="text-h6">{{ t('common.actions.import') }}</div>
      <div class="text-subtitle-1">
        {{ t('manage_user_assets.import.subtitle') }}
      </div>
      <file-upload
        class="mt-4"
        source="zip"
        file-filter=".zip"
        :uploaded="uploaded"
        :error-message="importError"
        @selected="zip = $event"
        @update:uploaded="uploaded = $event"
      />
      <v-btn
        color="primary"
        class="mt-4"
        :disabled="importDisabled"
        :loading="uploading"
        @click="importZip"
      >
        {{ t('common.actions.import') }}
      </v-btn>
    </v-sheet>
  </card>
</template>

<script setup lang="ts">
import FileUpload from '@/components/import/FileUpload.vue';
import { useAssets } from '@/store/assets';
import { assert } from '@/utils/assertions';

const zip = ref<File | null>(null);
const importError = ref('');
const exportError = ref('');
const downloading = ref(false);
const downloaded = ref(false);
const uploading = ref(false);
const uploaded = ref(false);

const { importCustomAssets, exportCustomAssets } = useAssets();
const importDisabled = computed(() => !get(zip));
const { start, stop } = useTimeoutFn(() => set(downloaded, false), 4000);

const importZip = async () => {
  const file = get(zip);
  assert(file);
  set(uploading, true);
  const result = await importCustomAssets(file);
  if (result.success) {
    set(uploaded, true);
  } else {
    set(importError, result.message);
  }
  set(uploading, false);
  set(zip, null);
};

const exportZip = async () => {
  stop();
  if (get(downloading)) {
    return;
  }
  set(downloading, true);
  let result = await exportCustomAssets();
  if (result.success) {
    set(downloaded, true);
    start();
  } else {
    set(exportError, result.message);
  }
  set(downloading, false);
};

const { t } = useI18n();
</script>

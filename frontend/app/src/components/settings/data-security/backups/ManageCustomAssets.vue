<template>
  <card>
    <template #title>{{ $t('manage_custom_assets.title') }}</template>

    <v-alert type="info" outlined dense>
      {{ $t('manage_custom_assets.warning') }}
    </v-alert>

    <v-sheet outlined class="pa-4" rounded>
      <div class="text-h6">{{ $t('manage_custom_assets.backup.title') }}</div>
      <div class="text-subtitle-1">
        {{ $t('manage_custom_assets.backup.subtitle') }}
      </div>
      <v-alert v-if="backupError" type="error" outlined dense>
        {{ backupError }}
      </v-alert>
      <div class="d-flex flex-row align-center mt-4">
        <v-btn color="primary" :loading="downloading" @click="backup">
          {{ $t('manage_custom_assets.backup.button') }}
        </v-btn>
        <v-icon v-if="downloaded" class="ms-4" color="success">
          mdi-check-circle
        </v-icon>
        <span v-if="downloaded" class="ms-2">
          {{ $t('manage_custom_assets.backup.success') }}
        </span>
      </div>
    </v-sheet>

    <v-sheet outlined class="pa-4 mt-4" rounded>
      <div class="text-h6">{{ $t('manage_custom_assets.restore.title') }}</div>
      <div class="text-subtitle-1">
        {{ $t('manage_custom_assets.restore.subtitle') }}
      </div>
      <file-upload
        class="mt-4"
        source="zip"
        file-filter=".zip"
        :uploaded="uploaded"
        :error-message="restoreError"
        @selected="zip = $event"
        @update:uploaded="uploaded = $event"
      />
      <v-btn
        color="primary"
        class="mt-4"
        :disabled="restoreDisabled"
        :loading="uploading"
        @click="restore"
      >
        {{ $t('manage_custom_assets.restore.button') }}
      </v-btn>
    </v-sheet>
  </card>
</template>

<script lang="ts">
import { computed, defineComponent, ref } from '@vue/composition-api';
import { get, set } from '@vueuse/core';
import FileUpload from '@/components/import/FileUpload.vue';
import { useAssets } from '@/store/assets';
import { assert } from '@/utils/assertions';

export default defineComponent({
  name: 'ManageCustomAssets',
  components: { FileUpload },
  setup() {
    const zip = ref<File | null>(null);
    const restoreError = ref('');
    const backupError = ref('');
    const downloading = ref(false);
    const downloaded = ref(false);
    const uploading = ref(false);
    const uploaded = ref(false);

    const { restoreCustomAssets, backupCustomAssets } = useAssets();

    const restoreDisabled = computed(() => !get(zip));

    const restore = async () => {
      const file = get(zip);
      assert(file);
      set(uploading, true);
      const result = await restoreCustomAssets(file);
      if (result.success) {
        set(uploaded, true);
      } else {
        set(restoreError, result.message);
      }
      set(uploading, false);
      set(zip, null);
    };

    const backup = async () => {
      if (get(downloading)) {
        return;
      }
      set(downloading, true);
      let result = await backupCustomAssets();
      if (result.success) {
        set(downloaded, true);
        setTimeout(() => {
          set(downloaded, false);
        }, 4000);
      } else {
        set(backupError, result.message);
      }
      set(downloading, false);
    };

    return {
      zip,
      downloading,
      downloaded,
      uploading,
      uploaded,
      backupError,
      restoreError,
      restoreDisabled,
      backup,
      restore
    };
  }
});
</script>

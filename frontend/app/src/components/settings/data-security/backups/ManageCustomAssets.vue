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
      <v-btn
        color="primary"
        class="mt-4"
        :loading="downloading"
        @click="backup"
      >
        {{ $t('manage_custom_assets.backup.button') }}
      </v-btn>
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
import { computed, defineComponent, ref, unref } from '@vue/composition-api';
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
    const uploading = ref(false);
    const uploaded = ref(false);

    const { restoreCustomAssets, backupCustomAssets } = useAssets();

    const restoreDisabled = computed(() => {
      return !unref(zip);
    });

    const restore = async () => {
      const file = unref(zip);
      assert(file);
      uploading.value = true;
      const result = await restoreCustomAssets(file);
      if (result.success) {
        uploaded.value = true;
      } else {
        restoreError.value = result.message;
      }
      uploading.value = false;
      zip.value = null;
    };

    const backup = async () => {
      if (unref(downloading)) {
        return;
      }
      downloading.value = true;
      let sucess = await backupCustomAssets();
      if (sucess.success) {
        //TODO
      } else {
        backupError.value = sucess.message;
      }
      downloading.value = false;
    };

    return {
      zip,
      downloading,
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

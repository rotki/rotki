<script setup lang="ts">
import { assert } from '@rotki/common';
import FileUpload from '@/components/import/FileUpload.vue';
import SettingsItem from '@/components/settings/controls/SettingsItem.vue';
import { useAssets } from '@/composables/assets';

const zip = ref<File>();
const importError = ref('');
const exportError = ref('');
const downloading = ref(false);
const downloaded = ref(false);
const uploading = ref(false);
const uploaded = ref(false);

const { exportCustomAssets, importCustomAssets } = useAssets();
const importDisabled = computed(() => !get(zip));
const { start, stop } = useTimeoutFn(() => set(downloaded, false), 4000);

async function importZip() {
  const file = get(zip);
  assert(file);
  set(uploading, true);
  const result = await importCustomAssets(file);
  if (result.success)
    set(uploaded, true);
  else set(importError, result.message);

  set(uploading, false);
  set(zip, null);
}

async function exportZip() {
  stop();
  if (get(downloading))
    return;

  set(downloading, true);
  const result = await exportCustomAssets();
  if (result.success) {
    set(downloaded, true);
    start();
  }
  else {
    set(exportError, result.message);
  }
  set(downloading, false);
}

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <RuiAlert
    type="info"
    class="mt-4"
  >
    {{ t('manage_user_assets.warning') }}
  </RuiAlert>

  <SettingsItem>
    <template #title>
      {{ t('manage_user_assets.export.title') }}
    </template>
    <template #subtitle>
      {{ t('manage_user_assets.export.subtitle') }}
    </template>
    <div class="flex flex-col gap-4 items-end">
      <RuiButton
        color="primary"
        :loading="downloading"
        @click="exportZip()"
      >
        {{ t('manage_user_assets.export.button') }}
      </RuiButton>
      <RuiAlert
        v-if="downloaded"
        type="success"
        class="w-full"
      >
        {{ t('manage_user_assets.export.success') }}
      </RuiAlert>
    </div>
  </SettingsItem>
  <SettingsItem>
    <template #title>
      {{ t('common.actions.import') }}
    </template>
    <template #subtitle>
      {{ t('manage_user_assets.import.subtitle') }}
    </template>
    <FileUpload
      v-model="zip"
      source="zip"
      file-filter=".zip"
      class="bg-white dark:bg-transparent"
      :uploaded="uploaded"
      :error-message="importError"
      @update:uploaded="uploaded = $event"
      @update:error-message="importError = $event"
    />
    <div class="flex justify-end">
      <RuiButton
        color="primary"
        class="mt-4"
        :disabled="importDisabled"
        :loading="uploading"
        @click="importZip()"
      >
        {{ t('common.actions.import') }}
      </RuiButton>
    </div>
  </SettingsItem>
</template>

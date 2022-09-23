<template>
  <v-btn
    class="mr-4 mb-sm-0 mb-4"
    color="primary"
    depressed
    :loading="isUpdateIgnoredAssetsLoading"
    :disabled="isUpdateIgnoredAssetsLoading"
    @click="update"
  >
    <v-icon class="mr-2">mdi-sync</v-icon>
    {{ tc('asset_management.sync_ignored_assets_list') }}
    <v-chip
      small
      class="ml-2 px-2 asset_management__ignored-assets__chip"
      color="white"
      text-color="primary"
    >
      {{ ignoredAssets.length }}
    </v-chip>
  </v-btn>
</template>

<script setup lang="ts">
import { useIgnoredAssetsStore } from '@/store/assets/ignored';
import { useTasks } from '@/store/tasks';
import { TaskType } from '@/types/task-type';

const emit = defineEmits(['refresh']);

const ignoredAssetsStore = useIgnoredAssetsStore();
const { ignoredAssets } = storeToRefs(ignoredAssetsStore);
const { isTaskRunning } = useTasks();
const { tc } = useI18n();

const update = async () => {
  await ignoredAssetsStore.updateIgnoredAssets();
  emit('refresh');
};

const isUpdateIgnoredAssetsLoading = isTaskRunning(
  TaskType.UPDATE_IGNORED_ASSETS
);
</script>

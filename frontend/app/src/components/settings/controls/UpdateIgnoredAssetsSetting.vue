<template>
  <div>
    <v-row no-gutters>
      <v-col cols="auto">
        {{ $t('accounting_settings.ignored_assets') }}
      </v-col>
      <v-col>
        <v-badge class="pl-2">
          <template #badge>
            <div class="accounting-settings__ignored-assets__badge">
              {{ ignoredAssets.length }}
            </div>
          </template>
        </v-badge>
      </v-col>
    </v-row>
    <div class="pt-6">
      <v-btn
        color="primary"
        :loading="isUpdateIgnoredAssetsLoading"
        :disabled="isUpdateIgnoredAssetsLoading"
        @click="updateIgnoredAssets"
      >
        {{ $t('accounting_settings.fetch_from_cryptoscamdb') }}
      </v-btn>
    </div>
  </div>
</template>

<script lang="ts">
import { defineComponent } from '@vue/composition-api';
import { storeToRefs } from 'pinia';
import { useIgnoredAssetsStore } from '@/store/assets';
import { useTasks } from '@/store/tasks';
import { TaskType } from '@/types/task-type';

export default defineComponent({
  name: 'UpdateIgnoredAssetsSetting',
  setup() {
    const store = useIgnoredAssetsStore();
    const { ignoredAssets } = storeToRefs(store);
    const { updateIgnoredAssets } = store;

    const { isTaskRunning } = useTasks();
    const isUpdateIgnoredAssetsLoading = isTaskRunning(
      TaskType.UPDATE_IGNORED_ASSETS
    );
    return {
      ignoredAssets,
      isUpdateIgnoredAssetsLoading,
      updateIgnoredAssets
    };
  }
});
</script>

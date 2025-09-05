<script setup lang="ts">
import SettingsItem from '@/components/settings/controls/SettingsItem.vue';
import SettingCategory from '@/components/settings/SettingCategory.vue';
import { useUnifiedProgress } from '@/modules/dashboard/progress/composables/use-unified-progress';
import HistoryQueryIndicatorDismissalThresholdSetting from './HistoryQueryIndicatorDismissalThresholdSetting.vue';
import HistoryQueryIndicatorMinOutOfSyncPeriodSetting from './HistoryQueryIndicatorMinOutOfSyncPeriodSetting.vue';

const { t } = useI18n({ useScope: 'global' });

const { resetQueryStatus } = useUnifiedProgress();

const showSuccess = ref<boolean>(false);
let successTimeout: ReturnType<typeof setTimeout> | undefined;

function handleReset(): void {
  resetQueryStatus();
  set(showSuccess, true);

  if (successTimeout) {
    clearTimeout(successTimeout);
  }

  successTimeout = setTimeout(() => {
    set(showSuccess, false);
  }, 5000);
}

onUnmounted(() => {
  if (successTimeout) {
    clearTimeout(successTimeout);
  }
});
</script>

<template>
  <SettingCategory class="mt-6">
    <template #title>
      {{ t('frontend_settings.history_query_indicator.title') }}
    </template>
    <HistoryQueryIndicatorMinOutOfSyncPeriodSetting />
    <HistoryQueryIndicatorDismissalThresholdSetting />
    <div>
      <SettingsItem>
        <template #title>
          {{ t('frontend_settings.history_query_indicator.reset_dismissal_status.title') }}
        </template>
        <template #subtitle>
          {{ t('frontend_settings.history_query_indicator.reset_dismissal_status.subtitle') }}
        </template>
        <div class="flex items-start flex-col gap-1">
          <RuiButton
            variant="outlined"
            color="secondary"
            :disabled="showSuccess"
            @click="handleReset()"
          >
            {{ t('frontend_settings.history_query_indicator.reset_dismissal_status.button') }}
          </RuiButton>
          <div
            v-if="showSuccess"
            class="text-rui-success text-caption"
          >
            {{
              t('frontend_settings.history_query_indicator.reset_dismissal_status.success') }}
          </div>
        </div>
      </SettingsItem>
    </div>
  </SettingCategory>
</template>

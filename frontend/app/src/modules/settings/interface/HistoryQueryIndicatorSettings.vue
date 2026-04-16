<script setup lang="ts">
import { useUnifiedProgress } from '@/modules/dashboard/progress/use-unified-progress';
import SettingsItem from '@/modules/settings/controls/SettingsItem.vue';
import { SettingsHighlightIds } from '@/modules/settings/setting-highlight-ids';
import SettingCategory from '@/modules/settings/SettingCategory.vue';
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
    <HistoryQueryIndicatorMinOutOfSyncPeriodSetting :id="SettingsHighlightIds.MIN_OUT_OF_SYNC_PERIOD" />
    <HistoryQueryIndicatorDismissalThresholdSetting :id="SettingsHighlightIds.DISMISSAL_THRESHOLD" />
    <div>
      <SettingsItem :id="SettingsHighlightIds.RESET_DISMISSAL_STATUS">
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

<script setup lang="ts">
import type { CurrentDbUpgradeProgress } from '@/modules/auth/login';

const {
  dataMigration = false,
  progress,
} = defineProps<{
  progress: CurrentDbUpgradeProgress | null;
  dataMigration?: boolean;
}>();

const { t } = useI18n({ useScope: 'global' });

const [DefineProgress, ReuseProgress] = createReusableTemplate<{
  updateProgress: CurrentDbUpgradeProgress;
  warning: string;
  current: string;
}>();

const multipleUpgrades = computed<boolean>(() => {
  if (progress) {
    const { fromVersion, toVersion } = progress;
    return toVersion - fromVersion > 1;
  }
  return false;
});
</script>

<template>
  <RuiCard
    v-if="progress"
    variant="flat"
    class="max-w-[29rem] mx-auto !bg-transparent"
  >
    <template #header>
      <span class="text-h6">
        {{ dataMigration ? t('login.migrating_data.title') : t('login.upgrading_db.title') }}
      </span>
    </template>
    <div class="flex items-start gap-4">
      <div class="relative inline-flex rotate-90 size-[45px] shrink-0">
        <RuiProgress
          :value="progress.percentage"
          color="primary"
          size="45"
          circular
          :variant="progress.totalSteps === 0 ? 'indeterminate' : 'determinate'"
        />
        <RuiProgress
          v-if="multipleUpgrades"
          :value="progress.totalPercentage"
          class="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2"
          color="primary"
          size="32"
          circular
        />
      </div>
      <div class="min-w-0 flex-1">
        <DefineProgress #default="{ updateProgress, warning, current }">
          <div class="text-body-1 font-medium break-words">
            {{ warning }}
          </div>
          <RuiDivider class="my-2" />
          <!-- hide the progress message when the reset signal is received from the backend -->
          <div
            v-if="updateProgress.totalSteps > 0"
            class="text-body-2 text-rui-text-secondary break-words"
          >
            {{ current }}
          </div>
          <p
            v-if="updateProgress.description"
            class="text-caption text-rui-text-secondary mt-2 break-words"
          >
            {{ updateProgress.description }}
          </p>
        </DefineProgress>
        <ReuseProgress
          v-if="!dataMigration"
          :update-progress="progress"
          :current="t('login.upgrading_db.current', { ...progress })"
          :warning="t('login.upgrading_db.warning', { ...progress })"
        />
        <ReuseProgress
          v-else
          :update-progress="progress"
          :current="t('login.migrating_data.current', { ...progress })"
          :warning="t('login.migrating_data.warning', { ...progress })"
        />
      </div>
    </div>
  </RuiCard>
</template>

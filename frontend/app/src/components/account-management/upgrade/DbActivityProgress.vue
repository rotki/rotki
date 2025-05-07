<script setup lang="ts">
import type { CurrentDbUpgradeProgress } from '@/types/login';

const props = withDefaults(defineProps<{
  progress: CurrentDbUpgradeProgress | null;
  dataMigration?: boolean;
}>(), {
  dataMigration: false,
});

const { t } = useI18n({ useScope: 'global' });

const { progress } = toRefs(props);

const [DefineProgress, ReuseProgress] = createReusableTemplate<{
  updateProgress: CurrentDbUpgradeProgress;
  warning: string;
  current: string;
}>();

const multipleUpgrades = computed<boolean>(() => {
  if (isDefined(progress)) {
    const { fromVersion, toVersion } = get(progress);
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
      <span v-if="dataMigration">{{ t('login.migrating_data.title') }} </span>
      <span v-else> {{ t('login.upgrading_db.title') }}</span>
    </template>
    <div class="flex space-x-4 break-all">
      <div class="flex flex-col">
        <div class="relative inline-flex rotate-90">
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
            class="top-[0.40625rem] left-[0.40625rem] absolute"
            color="primary"
            circular
          />
        </div>
      </div>
      <div class="text-body-1">
        <DefineProgress #default="{ updateProgress, warning, current }">
          <div>
            {{ warning }}
          </div>
          <RuiDivider class="my-2" />
          <!-- hide the progress message when the reset signal is received from the backend -->
          <div
            v-if="updateProgress.totalSteps > 0"
            class="break-words"
          >
            {{ current }}
          </div>
          <ul
            v-if="updateProgress.description"
            class="-ml-2 mt-2 list-disc"
          >
            <li>{{ updateProgress.description }}</li>
          </ul>
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

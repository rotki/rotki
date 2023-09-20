<script setup lang="ts">
import { type CurrentDbUpgradeProgress } from '@/types/login';

const props = withDefaults(
  defineProps<{
    progress: CurrentDbUpgradeProgress | null;
    dataMigration?: boolean;
  }>(),
  {
    dataMigration: false
  }
);

const { t } = useI18n();

const { progress } = toRefs(props);

const multipleUpgrades = computed(() => {
  if (isDefined(progress)) {
    const { toVersion, fromVersion } = get(progress);
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
    <div class="flex space-x-4">
      <div class="flex flex-col">
        <div class="relative inline-flex rotate-90">
          <RuiProgress
            :value="progress.percentage"
            color="primary"
            size="45"
            circular
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
        <template v-if="!dataMigration">
          <div>
            {{ t('login.upgrading_db.warning', { ...progress }) }}
          </div>
          <div
            class="my-2 border-t border-black/[.12] dark:border-white/[.12]"
          />
          <div>
            {{ t('login.upgrading_db.current', { ...progress }) }}
          </div>
        </template>
        <template v-else>
          <div>
            {{ t('login.migrating_data.warning', { ...progress }) }}
          </div>
          <div
            class="my-2 border-t border-black/[.12] dark:border-white/[.12]"
          />
          <div>
            {{ t('login.migrating_data.current', { ...progress }) }}
          </div>
          <ul v-if="progress.description" class="-ml-2">
            <li>{{ progress.description }}</li>
          </ul>
        </template>
      </div>
    </div>
  </RuiCard>
</template>

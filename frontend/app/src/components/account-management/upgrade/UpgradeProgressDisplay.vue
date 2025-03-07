<script setup lang="ts">
import type { CurrentDbUpgradeProgress } from '@/types/login';
import DbActivityProgress from '@/components/account-management/upgrade/DbActivityProgress.vue';
import { useNewlyDetectedTokens } from '@/composables/assets/newly-detected-tokens';
import { useSessionAuthStore } from '@/store/session/auth';

const { dataMigrationStatus, dbUpgradeStatus } = storeToRefs(useSessionAuthStore());

const dbUpgradeProgressData = computed<CurrentDbUpgradeProgress | null>(() => {
  const status = get(dbUpgradeStatus);

  if (!status)
    return null;

  const { currentStep, description, totalSteps, toVersion } = status.currentUpgrade;
  const current = toVersion - status.startVersion;
  const total = status.targetVersion - status.startVersion;
  return {
    currentStep,
    currentVersion: toVersion,
    description: description || '',
    fromVersion: status.startVersion - 1,
    percentage: (currentStep / totalSteps) * 100,
    totalPercentage: (current / total) * 100,
    totalSteps,
    toVersion: status.targetVersion,
  };
});

const dataMigrationStatusData = computed<CurrentDbUpgradeProgress | null>(() => {
  const status = get(dataMigrationStatus);

  if (!status)
    return null;

  const { currentStep, description, totalSteps, version } = status.currentMigration;
  const current = version - status.startVersion;
  const total = status.targetVersion - status.startVersion;
  return {
    currentStep,
    currentVersion: version,
    description: description || '',
    fromVersion: status.startVersion,
    percentage: totalSteps === 0 ? 0 : (currentStep / totalSteps) * 100,
    totalPercentage: total === 0 ? 0 : (current / total) * 100,
    totalSteps,
    toVersion: status.targetVersion,
  };
});

const { clearInternalTokens } = useNewlyDetectedTokens();

onMounted(() => {
  if (get(dbUpgradeStatus))
    clearInternalTokens();
});
</script>

<template>
  <DbActivityProgress
    v-if="dataMigrationStatusData"
    data-migration
    :progress="dataMigrationStatusData"
  />
  <DbActivityProgress
    v-else
    :progress="dbUpgradeProgressData"
  />
</template>

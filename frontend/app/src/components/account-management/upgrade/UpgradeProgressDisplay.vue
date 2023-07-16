<script setup lang="ts">
import { type ComputedRef } from 'vue';
import { type CurrentDbUpgradeProgress } from '@/types/login';

const { dbUpgradeStatus, dataMigrationStatus } = storeToRefs(
  useSessionAuthStore()
);

const dbUpgradeProgressData: ComputedRef<CurrentDbUpgradeProgress | null> =
  computed(() => {
    const status = get(dbUpgradeStatus);

    if (!status) {
      return null;
    }
    const { currentStep, toVersion, totalSteps } = status.currentUpgrade;
    const current = toVersion - status.startVersion;
    const total = status.targetVersion - status.startVersion;
    return {
      percentage: (currentStep / totalSteps) * 100,
      totalPercentage: (current / total) * 100,
      currentVersion: toVersion,
      fromVersion: status.startVersion - 1,
      toVersion: status.targetVersion,
      currentStep: totalSteps > 0 ? currentStep : 1,
      totalSteps: totalSteps > 0 ? totalSteps : 1
    };
  });

const dataMigrationStatusData: ComputedRef<CurrentDbUpgradeProgress | null> =
  computed(() => {
    const status = get(dataMigrationStatus);

    if (!status) {
      return null;
    }
    const { currentStep, version, totalSteps, description } =
      status.currentMigration;
    const current = version - status.startVersion;
    const total = status.targetVersion - status.startVersion;
    return {
      percentage: totalSteps === 0 ? 0 : (currentStep / totalSteps) * 100,
      totalPercentage: total === 0 ? 0 : (current / total) * 100,
      currentVersion: version,
      fromVersion: status.startVersion,
      toVersion: status.targetVersion,
      currentStep: totalSteps > 0 ? currentStep : 1,
      totalSteps: totalSteps > 0 ? totalSteps : 1,
      description: description || ''
    };
  });

const { clearInternalTokens } = useNewlyDetectedTokens();

onMounted(() => {
  if (get(dbUpgradeStatus)) {
    clearInternalTokens();
  }
});
</script>

<template>
  <DbActivityProgress
    v-if="dataMigrationStatusData"
    data-migration
    :progress="dataMigrationStatusData"
  />
  <DbActivityProgress v-else :progress="dbUpgradeProgressData" />
</template>

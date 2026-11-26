<script setup lang="ts">
import type { SyncApproval } from '@/modules/auth/login';
import IncompleteUpgradeAlert from '@/modules/auth/login/IncompleteUpgradeAlert.vue';
import PremiumSyncConflictAlert from '@/modules/auth/login/PremiumSyncConflictAlert.vue';
import { useSessionAuthStore } from '@/modules/auth/use-session-auth-store';

const emit = defineEmits<{
  login: [actions: { syncApproval?: SyncApproval; resumeFromBackup?: boolean }];
}>();

const { resetIncompleteUpgradeConflict, resetSyncConflict } = useSessionAuthStore();

function abortLogin() {
  resetSyncConflict();
  resetIncompleteUpgradeConflict();
}
</script>

<template>
  <PremiumSyncConflictAlert @proceed="emit('login', { syncApproval: $event })" />

  <IncompleteUpgradeAlert
    @confirm="emit('login', { resumeFromBackup: true })"
    @cancel="abortLogin()"
  />
</template>

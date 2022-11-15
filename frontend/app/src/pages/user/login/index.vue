<template>
  <login-form
    :loading="loading"
    :sync-conflict="syncConflict"
    :errors="errors"
    :show-upgrade-message="showUpgradeMessage"
    @touched="errors = []"
    @login="userLogin($event)"
    @backend-changed="backendChanged($event)"
    @new-account="navigateToUserCreation()"
  />
</template>

<script setup lang="ts">
import LoginForm from '@/components/account-management/LoginForm.vue';
import { useBackendManagement } from '@/composables/backend';
import { useAppNavigation } from '@/composables/navigation';
import { useAccountManagement } from '@/composables/user/account';
import { useUpgradeMessage } from '@/composables/user/upgrade';
import { useSessionAuthStore } from '@/store/session/auth';

const { navigateToUserCreation } = useAppNavigation();
const { syncConflict } = storeToRefs(useSessionAuthStore());
const { backendChanged } = useBackendManagement();
const { userLogin, errors, loading } = useAccountManagement();
const { showUpgradeMessage } = useUpgradeMessage(loading);
</script>

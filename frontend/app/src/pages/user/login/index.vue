<template>
  <login-form
    :loading="loading"
    :sync-conflict="syncConflict"
    :errors="errors"
    :login-status="loginStatus"
    @touched="errors = []"
    @login="userLogin($event)"
    @backend-changed="backendChanged($event)"
    @new-account="navigateToUserCreation()"
  />
</template>

<script setup lang="ts">
import LoginForm from '@/components/account-management/LoginForm.vue';
import { useSessionAuthStore } from '@/store/session/auth';

const { navigateToUserCreation } = useAppNavigation();
const { syncConflict, loginStatus } = storeToRefs(useSessionAuthStore());
const { backendChanged } = useBackendManagement();
const { userLogin, errors, loading } = useAccountManagement();
</script>

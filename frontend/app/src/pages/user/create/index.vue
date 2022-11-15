<template>
  <create-account-form
    :loading="loading"
    :error="error"
    @error:clear="error = ''"
    @cancel="navigateToUserLogin()"
    @confirm="createNewAccount($event)"
  />
</template>

<script setup lang="ts">
import CreateAccountForm from '@/components/account-management/CreateAccountForm.vue';
import { useAppNavigation } from '@/composables/navigation';
import { useAccountManagement } from '@/composables/user/account';

const { navigateToUserLogin } = useAppNavigation();
const { createNewAccount, error, loading } = useAccountManagement();
</script>

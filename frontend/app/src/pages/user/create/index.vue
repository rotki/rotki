<script setup lang="ts">
import Fragment from '@/components/helper/Fragment';

const { upgradeVisible } = storeToRefs(useSessionAuthStore());
const { navigateToUserLogin } = useAppNavigation();
const { createNewAccount, error, loading } = useAccountManagement();
</script>

<template>
  <Fragment>
    <UpgradeProgressDisplay v-if="upgradeVisible" />
    <CreateAccountForm
      v-else
      :loading="loading"
      :error="error"
      @error:clear="error = ''"
      @cancel="navigateToUserLogin()"
      @confirm="createNewAccount($event)"
    />
  </Fragment>
</template>

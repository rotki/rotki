<script setup lang="ts">
import Fragment from '@/components/helper/Fragment';

const { upgradeVisible } = storeToRefs(useSessionAuthStore());
const { navigateToUserLogin } = useAppNavigation();
const { createNewAccount, error, loading } = useAccountManagement();
</script>

<template>
  <fragment>
    <upgrade-progress-display v-if="upgradeVisible" />
    <create-account-form
      v-else
      :loading="loading"
      :error="error"
      @error:clear="error = ''"
      @cancel="navigateToUserLogin()"
      @confirm="createNewAccount($event)"
    />
  </fragment>
</template>

<script setup lang="ts">
import LoginActionAlert from '@/components/account-management/login/LoginActionAlert.vue';
import { useSessionAuthStore } from '@/store/session/auth';

const emit = defineEmits<{ confirm: []; cancel: [] }>();

const { t } = useI18n({ useScope: 'global' });

const { incompleteUpgradeConflict } = storeToRefs(useSessionAuthStore());
</script>

<template>
  <Transition>
    <LoginActionAlert
      v-if="incompleteUpgradeConflict"
      icon="lu-triangle-alert"
      @confirm="emit('confirm')"
      @cancel="emit('cancel')"
    >
      <template #title>
        {{ t('login.incomplete_upgrade_error.title') }}
      </template>
      <template #cancel>
        {{ t('login.incomplete_upgrade_error.abort') }}
      </template>
      <template #confirm>
        {{ t('login.incomplete_upgrade_error.resume') }}
      </template>

      <div>{{ incompleteUpgradeConflict.message }}</div>
      <div class="mt-2">
        {{ t('login.incomplete_upgrade_error.question') }}
      </div>
    </LoginActionAlert>
  </Transition>
</template>

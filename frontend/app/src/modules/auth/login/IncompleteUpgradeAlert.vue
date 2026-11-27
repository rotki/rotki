<script setup lang="ts">
import { storeToRefs } from 'pinia';
import { useI18n } from 'vue-i18n';
import LoginActionAlert from '@/modules/auth/login/LoginActionAlert.vue';
import { useSessionAuthStore } from '@/modules/auth/use-session-auth-store';

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

      <p class="break-words">
        {{ incompleteUpgradeConflict.message }}
      </p>
      <p>{{ t('login.incomplete_upgrade_error.question') }}</p>
    </LoginActionAlert>
  </Transition>
</template>

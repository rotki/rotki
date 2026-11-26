<script setup lang="ts">
import { RuiAlert } from '@rotki/ui-library';
import { useI18n } from 'vue-i18n';
import { useAutoLogoutNotice } from '@/modules/auth/auto-logout/use-auto-logout-notice';

const { t } = useI18n({ useScope: 'global' });

const { dismiss, idleMinutes } = useAutoLogoutNotice();
</script>

<template>
  <RuiAlert
    v-if="idleMinutes"
    type="info"
    class="mb-6"
    closeable
    data-testid="auto-logout-notice"
    @close="dismiss()"
  >
    {{ t('login.auto_logout_notice', { minutes: idleMinutes }, idleMinutes) }}
  </RuiAlert>
</template>

<script setup lang="ts">
import { get } from '@vueuse/shared';
import { computed } from 'vue';
import { useI18n } from 'vue-i18n';
import AccountManagementAside from '@/modules/auth/AccountManagementAside.vue';
import NewReleaseChangelog from '@/modules/auth/login/NewReleaseChangelog.vue';
import WelcomeMessageDisplay from '@/modules/auth/login/WelcomeMessageDisplay.vue';
import { useDynamicMessages } from '@/modules/core/messaging/use-dynamic-messages';
import { useUpdateMessage } from '@/modules/core/messaging/use-update-message';
import RotkiLogo from '@/modules/shell/components/RotkiLogo.vue';

const { t } = useI18n({ useScope: 'global' });
const { activeWelcomeMessages, welcomeHeader, welcomeMessage } = useDynamicMessages();
const { showReleaseNotes } = useUpdateMessage();

const header = computed<{ header: string; text: string }>(() => {
  const header = get(welcomeHeader);
  return {
    header: header?.header || t('login.welcome_title'),
    text: header?.text || t('login.welcome_description'),
  };
});
</script>

<template>
  <AccountManagementAside>
    <RotkiLogo
      class="mb-10"
      size="2"
      unique-key="0"
      text
    />
    <h2 class="text-h5 mb-3">
      {{ header.header }}
    </h2>
    <p class="text-body-1 text-rui-text-secondary">
      {{ header.text }}
    </p>
    <NewReleaseChangelog
      v-if="showReleaseNotes"
      class="mt-4"
    />
    <WelcomeMessageDisplay
      v-else-if="welcomeMessage"
      class="mt-6"
      :messages="activeWelcomeMessages"
    />
  </AccountManagementAside>
</template>

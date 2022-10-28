<template>
  <div>
    <v-menu
      id="user-dropdown"
      content-class="user-dropdown__menu"
      transition="slide-y-transition"
      max-width="300px"
      min-width="180px"
      offset-y
    >
      <template #activator="{ on }">
        <menu-tooltip-button
          tooltip="Account"
          class-name="user-dropdown secondary--text text--lighten-4"
          :on-menu="on"
        >
          <v-icon>mdi-account-circle</v-icon>
        </menu-tooltip-button>
      </template>
      <v-list data-cy="user-dropdown">
        <v-list-item key="username" class="user-username">
          <v-list-item-title class="font-weight-bold text-center">
            {{ username }}
          </v-list-item-title>
        </v-list-item>
        <v-divider class="mx-4" />
        <v-list-item
          key="settings"
          class="user-dropdown__settings"
          to="/settings/general"
        >
          <v-list-item-avatar>
            <v-icon color="primary">mdi-cog</v-icon>
          </v-list-item-avatar>
          <v-list-item-title>
            {{ t('user_dropdown.settings') }}
          </v-list-item-title>
        </v-list-item>

        <v-list-item
          v-if="xsOnly"
          key="privacy-mode"
          @click="togglePrivacyMode"
        >
          <v-list-item-avatar>
            <v-icon color="primary"> {{ privacyModeIcon }}</v-icon>
          </v-list-item-avatar>
          <v-list-item-title>
            {{ t('user_dropdown.change_privacy_mode.label') }}
          </v-list-item-title>
        </v-list-item>

        <theme-control v-if="xsOnly" :dark-mode-enabled="darkModeEnabled" menu>
          {{ t('user_dropdown.switch_theme') }}
        </theme-control>

        <v-divider class="mx-4" />
        <v-list-item
          key="logout"
          class="user-dropdown__logout"
          @click="confirmLogout = true"
        >
          <v-list-item-avatar>
            <v-icon color="primary">mdi-logout-variant</v-icon>
          </v-list-item-avatar>
          <v-list-item-title>
            {{ t('user_dropdown.logout') }}
          </v-list-item-title>
        </v-list-item>
      </v-list>
    </v-menu>
    <confirm-dialog
      :display="confirmLogout"
      :title="tc('user_dropdown.confirmation.title')"
      :message="tc('user_dropdown.confirmation.message')"
      @confirm="logoutHandler()"
      @cancel="confirmLogout = false"
    />
  </div>
</template>

<script setup lang="ts">
import ConfirmDialog from '@/components/dialogs/ConfirmDialog.vue';
import MenuTooltipButton from '@/components/helper/MenuTooltipButton.vue';
import ThemeControl from '@/components/premium/ThemeControl.vue';
import { useTheme } from '@/composables/common';
import { useDarkMode } from '@/composables/dark-mode';
import { usePrivacyMode } from '@/composables/privacy';
import { useRoute, useRouter } from '@/composables/router';
import { interop } from '@/electron-interop';
import { useSessionStore } from '@/store/session';

const { t, tc } = useI18n();

const KEY_REMEMBER_PASSWORD = 'rotki.remember_password';

const store = useSessionStore();
const { username } = storeToRefs(store);
const confirmLogout = ref<boolean>(false);
const router = useRouter();
const route = useRoute();
const { privacyModeIcon, togglePrivacyMode } = usePrivacyMode();
const { currentBreakpoint } = useTheme();
const xsOnly = computed(() => get(currentBreakpoint).xsOnly);

const savedRememberPassword = useLocalStorage(KEY_REMEMBER_PASSWORD, null);

const logoutHandler = async () => {
  if (interop.isPackaged && get(savedRememberPassword)) {
    await interop.clearPassword();
  }

  set(confirmLogout, false);
  await store.logout();

  if (get(route).path !== '/') {
    await router.replace('/');
  }
};

const { darkModeEnabled } = useDarkMode();
</script>

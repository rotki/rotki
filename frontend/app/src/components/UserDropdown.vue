<template>
  <div>
    <v-menu
      id="user-dropdown"
      content-class="user-dropdown__menu"
      transition="slide-y-transition"
      max-width="180px"
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
            {{ $t('user_dropdown.settings') }}
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
            {{ $t('user_dropdown.change_privacy_mode.label') }}
          </v-list-item-title>
        </v-list-item>

        <v-list-item v-if="xsOnly">
          <v-list-item-avatar>
            <theme-control :dark-mode-enabled="darkModeEnabled" menu />
          </v-list-item-avatar>
          <v-list-item-title>
            {{ $t('user_dropdown.switch_theme') }}
          </v-list-item-title>
        </v-list-item>

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
            {{ $t('user_dropdown.logout') }}
          </v-list-item-title>
        </v-list-item>
      </v-list>
    </v-menu>
    <confirm-dialog
      :display="confirmLogout"
      :title="$tc('user_dropdown.confirmation.title')"
      :message="$tc('user_dropdown.confirmation.message')"
      @confirm="logoutHandler()"
      @cancel="confirmLogout = false"
    />
  </div>
</template>

<script lang="ts">
import { computed, defineComponent, ref } from '@vue/composition-api';
import { get, set, useLocalStorage } from '@vueuse/core';
import ConfirmDialog from '@/components/dialogs/ConfirmDialog.vue';
import MenuTooltipButton from '@/components/helper/MenuTooltipButton.vue';
import ThemeControl from '@/components/premium/ThemeControl.vue';
import { setupThemeCheck, useRoute, useRouter } from '@/composables/common';
import { usePrivacyMode } from '@/composables/privacy';
import { setupSession, useDarkMode } from '@/composables/session';
import { interop } from '@/electron-interop';

const KEY_REMEMBER_PASSWORD = 'rotki.remember_password';

export default defineComponent({
  name: 'UserDropdown',
  components: {
    ThemeControl,
    ConfirmDialog,
    MenuTooltipButton
  },
  setup() {
    const { username, logout } = setupSession();
    const confirmLogout = ref<boolean>(false);
    const router = useRouter();
    const route = useRoute();
    const { privacyModeIcon, togglePrivacyMode } = usePrivacyMode();
    const { currentBreakpoint } = setupThemeCheck();
    const xsOnly = computed(() => get(currentBreakpoint).xsOnly);

    const savedRememberPassword = useLocalStorage(KEY_REMEMBER_PASSWORD, null);

    const logoutHandler = async () => {
      if (interop.isPackaged && get(savedRememberPassword)) {
        await interop.clearPassword();
      }

      set(confirmLogout, false);
      await logout();

      if (get(route).path !== '/') {
        router.replace('/');
      }
    };

    return {
      confirmLogout,
      username,
      privacyModeIcon,
      xsOnly,
      togglePrivacyMode,
      logoutHandler,
      ...useDarkMode()
    };
  }
});
</script>

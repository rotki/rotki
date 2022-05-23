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
import { defineComponent, ref } from '@vue/composition-api';
import { get, set } from '@vueuse/core';
import ConfirmDialog from '@/components/dialogs/ConfirmDialog.vue';
import MenuTooltipButton from '@/components/helper/MenuTooltipButton.vue';

import { useRoute, useRouter } from '@/composables/common';
import { setupSession } from '@/composables/session';
import { interop } from '@/electron-interop';

export default defineComponent({
  name: 'UserDropdown',
  components: {
    ConfirmDialog,
    MenuTooltipButton
  },
  setup() {
    const { username, logout } = setupSession();
    const confirmLogout = ref<boolean>(false);
    const router = useRouter();
    const route = useRoute();

    const logoutHandler = async () => {
      if (interop.isPackaged) {
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
      logoutHandler
    };
  }
});
</script>

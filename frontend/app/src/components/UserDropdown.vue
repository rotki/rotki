<script setup lang="ts">
const { t } = useI18n();

const KEY_REMEMBER_PASSWORD = 'rotki.remember_password';

const { logout } = useSessionStore();
const { username } = storeToRefs(useSessionAuthStore());
const { isPackaged, clearPassword } = useInterop();
const { privacyModeIcon, togglePrivacyMode } = usePrivacyMode();
const { xs } = useDisplay();
const { navigateToUserLogin } = useAppNavigation();

const savedRememberPassword = useLocalStorage(KEY_REMEMBER_PASSWORD, null);

const { show } = useConfirmStore();

const showConfirmation = () =>
  show(
    {
      title: t('user_dropdown.confirmation.title'),
      message: t('user_dropdown.confirmation.message'),
      type: 'info'
    },
    async () => {
      if (isPackaged && get(savedRememberPassword)) {
        await clearPassword();
      }

      await Promise.all([logout(), navigateToUserLogin()]);
    }
  );

const { darkModeEnabled } = useDarkMode();
</script>

<template>
  <div>
    <VMenu
      id="user-dropdown"
      content-class="user-dropdown__menu"
      transition="slide-y-transition"
      max-width="300px"
      min-width="180px"
      offset-y
    >
      <template #activator="{ on }">
        <MenuTooltipButton
          tooltip="Account"
          class-name="user-dropdown secondary--text text--lighten-4"
          :on-menu="on"
        >
          <RuiIcon name="account-circle-line" />
        </MenuTooltipButton>
      </template>
      <VList data-cy="user-dropdown">
        <VListItem key="username" class="user-username">
          <VListItemTitle class="font-bold text-center">
            {{ username }}
          </VListItemTitle>
        </VListItem>
        <RuiDivider />
        <VListItem
          key="settings"
          class="user-dropdown__settings px-6 py-1"
          to="/settings/general"
        >
          <VListItemAvatar size="24">
            <RuiIcon color="primary" name="settings-4-line" />
          </VListItemAvatar>
          <VListItemTitle>
            {{ t('user_dropdown.settings') }}
          </VListItemTitle>
        </VListItem>

        <VListItem
          v-if="xs"
          key="privacy-mode"
          class="px-6 py-1"
          @click="togglePrivacyMode()"
        >
          <VListItemAvatar size="24">
            <RuiIcon color="primary" :name="privacyModeIcon" />
          </VListItemAvatar>
          <VListItemTitle>
            {{ t('user_dropdown.change_privacy_mode.label') }}
          </VListItemTitle>
        </VListItem>

        <ThemeControl v-if="xs" :dark-mode-enabled="darkModeEnabled" menu>
          {{ t('user_dropdown.switch_theme') }}
        </ThemeControl>

        <RuiDivider />
        <VListItem
          key="logout"
          class="user-dropdown__logout px-6 py-1"
          @click="showConfirmation()"
        >
          <VListItemAvatar size="24">
            <RuiIcon color="primary" name="logout-box-r-line" />
          </VListItemAvatar>
          <VListItemTitle>
            {{ t('user_dropdown.logout') }}
          </VListItemTitle>
        </VListItem>
      </VList>
    </VMenu>
  </div>
</template>

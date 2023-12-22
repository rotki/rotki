<script setup lang="ts">
const { t } = useI18n();

const KEY_REMEMBER_PASSWORD = 'rotki.remember_password';

const { logout } = useSessionStore();
const { username } = storeToRefs(useSessionAuthStore());
const { isPackaged, clearPassword } = useInterop();
const { privacyModeIcon, togglePrivacyMode } = usePrivacyMode();
const { xs } = useDisplay();

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

      await logout();
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
        <div key="username" class="py-3 user-username font-bold text-center">
          {{ username }}
        </div>
        <RuiDivider />
        <RouterLink to="/settings/general">
          <RuiButton
            key="settings"
            variant="list"
            class="user-dropdown__settings"
          >
            <template #prepend>
              <RuiIcon color="primary" name="settings-4-line" />
            </template>
            {{ t('user_dropdown.settings') }}
          </RuiButton>
        </RouterLink>

        <RuiButton
          v-if="xs"
          key="privacy-mode"
          variant="list"
          @click="togglePrivacyMode()"
        >
          <template #prepend>
            <RuiIcon color="primary" :name="privacyModeIcon" />
          </template>
          {{ t('user_dropdown.change_privacy_mode.label') }}
        </RuiButton>

        <ThemeControl v-if="xs" :dark-mode-enabled="darkModeEnabled" menu>
          {{ t('user_dropdown.switch_theme') }}
        </ThemeControl>

        <RuiDivider />
        <RuiButton
          key="logout"
          variant="list"
          class="user-dropdown__logout"
          @click="showConfirmation()"
        >
          <template #prepend>
            <RuiIcon color="primary" name="logout-box-r-line" />
          </template>
          {{ t('user_dropdown.logout') }}
        </RuiButton>
      </VList>
    </VMenu>
  </div>
</template>

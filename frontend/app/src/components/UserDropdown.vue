<script setup lang="ts">
import { useBreakpoint } from '@rotki/ui-library';

const { t } = useI18n();

const KEY_REMEMBER_PASSWORD = 'rotki.remember_password';

const { logout } = useSessionStore();
const { username } = storeToRefs(useSessionAuthStore());
const { isPackaged, clearPassword } = useInterop();
const { privacyModeIcon, togglePrivacyMode } = usePrivacyMode();
const { isXs } = useBreakpoint();

const savedRememberPassword = useLocalStorage(KEY_REMEMBER_PASSWORD, null);

const { show } = useConfirmStore();

function showConfirmation() {
  return show(
    {
      title: t('user_dropdown.confirmation.title'),
      message: t('user_dropdown.confirmation.message'),
      type: 'info',
    },
    async () => {
      if (isPackaged && get(savedRememberPassword))
        await clearPassword();

      await logout();
    },
  );
}

const { darkModeEnabled } = useDarkMode();
</script>

<template>
  <div>
    <RuiMenu
      id="user-dropdown"
      menu-class="user-dropdown__menu min-w-[10rem] max-w-[22rem]"
      close-on-content-click
    >
      <template #activator="{ attrs }">
        <MenuTooltipButton
          tooltip="Account"
          class-name="user-dropdown"
          v-bind="attrs"
        >
          <RuiIcon name="account-circle-line" />
        </MenuTooltipButton>
      </template>
      <div
        data-cy="user-dropdown"
        class="py-2"
      >
        <div
          key="username"
          class="py-3 user-username font-bold text-center"
        >
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
              <RuiIcon
                color="primary"
                name="settings-4-line"
              />
            </template>
            {{ t('user_dropdown.settings') }}
          </RuiButton>
        </RouterLink>

        <RuiButton
          v-if="isXs"
          key="privacy-mode"
          variant="list"
          @click="togglePrivacyMode()"
        >
          <template #prepend>
            <RuiIcon
              color="primary"
              :name="privacyModeIcon"
            />
          </template>
          {{ t('user_dropdown.change_privacy_mode.label') }}
        </RuiButton>

        <ThemeControl
          v-if="isXs"
          :dark-mode-enabled="darkModeEnabled"
          menu
        >
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
            <RuiIcon
              color="primary"
              name="logout-box-r-line"
            />
          </template>
          {{ t('user_dropdown.logout') }}
        </RuiButton>
      </div>
    </RuiMenu>
  </div>
</template>

<script setup lang="ts">
import { externalLinks } from '@shared/external-links';
import ExternalLink from '@/components/helper/ExternalLink.vue';
import MenuTooltipButton from '@/components/helper/MenuTooltipButton.vue';
import { useInterop } from '@/composables/electron-interop';
import { usePremiumHelper } from '@/composables/premium';
import { usePrivacyMode } from '@/composables/privacy';
import { useRememberSettings } from '@/composables/user/use-remember-settings';
import { useLogout } from '@/modules/account/use-logout';
import ThemeControl from '@/modules/theme/ThemeControl.vue';
import { useConfirmStore } from '@/store/confirm';
import { useSessionAuthStore } from '@/store/session/auth';

const { t } = useI18n({ useScope: 'global' });

const { logout } = useLogout();
const { username } = storeToRefs(useSessionAuthStore());
const { clearPassword, isPackaged } = useInterop();
const { privacyModeIcon, togglePrivacyMode } = usePrivacyMode();
const { isXs } = useBreakpoint();

const { savedRememberPassword } = useRememberSettings();
const { currentTier, premium } = usePremiumHelper();

const tierLabel = computed<string>(() => {
  const tier = get(currentTier);
  return tier ? t('premium_placeholder.current_plan', { tier }) : '';
});

const { show } = useConfirmStore();

function showConfirmation() {
  show(
    {
      message: t('user_dropdown.confirmation.message'),
      title: t('user_dropdown.confirmation.title'),
      type: 'info',
    },
    async () => {
      if (isPackaged && get(savedRememberPassword))
        await clearPassword();

      await logout();
    },
  );
}

const { isDark } = useRotkiTheme();
</script>

<template>
  <div>
    <RuiMenu
      data-cy="user-menu"
      menu-class="min-w-[10rem] max-w-[22rem]"
      close-on-content-click
    >
      <template #activator="{ attrs }">
        <MenuTooltipButton
          tooltip="Account"
          data-cy="user-menu-button"
          v-bind="attrs"
        >
          <RuiIcon name="lu-circle-user" />
        </MenuTooltipButton>
      </template>
      <div
        data-cy="user-dropdown"
        class="py-2"
      >
        <div class="py-3 flex flex-col items-center gap-1">
          <div
            data-cy="username"
            class="font-bold"
          >
            {{ username }}
          </div>
          <ExternalLink
            v-if="premium && tierLabel"
            custom
            :url="externalLinks.manageSubscriptions"
          >
            <RuiChip
              size="sm"
              variant="outlined"
              color="primary"
              class="!cursor-pointer"
            >
              {{ tierLabel }}
            </RuiChip>
          </ExternalLink>
        </div>
        <RuiDivider />
        <RouterLink :to="{ path: '/settings' }">
          <RuiButton
            variant="list"
            data-cy="settings-button"
          >
            <template #prepend>
              <RuiIcon
                color="primary"
                name="lu-settings"
              />
            </template>
            {{ t('user_dropdown.settings') }}
          </RuiButton>
        </RouterLink>

        <RuiButton
          v-if="isXs"
          data-cy="privacy-mode-button"
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
          :dark-mode-enabled="isDark"
          menu
          data-cy="theme-control"
        >
          {{ t('user_dropdown.switch_theme') }}
        </ThemeControl>
        <RuiDivider />
        <RuiButton
          variant="list"
          data-cy="logout-button"
          @click="showConfirmation()"
        >
          <template #prepend>
            <RuiIcon
              color="primary"
              name="lu-log-out"
            />
          </template>
          {{ t('user_dropdown.logout') }}
        </RuiButton>
      </div>
    </RuiMenu>
  </div>
</template>

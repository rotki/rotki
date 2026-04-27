<script setup lang="ts">
import { externalLinks } from '@shared/external-links';
import { useLogout } from '@/modules/auth/use-logout';
import { useRememberSettings } from '@/modules/auth/use-remember-settings';
import { useSessionAuthStore } from '@/modules/auth/use-session-auth-store';
import { useConfirmStore } from '@/modules/core/common/use-confirm-store';
import { usePremiumHelper } from '@/modules/premium/use-premium-helper';
import { usePrivacyMode } from '@/modules/settings/use-privacy';
import { useInterop } from '@/modules/shell/app/use-electron-interop';
import ExternalLink from '@/modules/shell/components/ExternalLink.vue';
import MenuTooltipButton from '@/modules/shell/components/MenuTooltipButton.vue';
import ThemeControl from '@/modules/shell/theme/ThemeControl.vue';

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
      <div data-cy="user-dropdown">
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
        <RouterLink
          #default="{ navigate }"
          :to="{ path: '/settings' }"
          custom
        >
          <!-- TODO: drop the `[&_[data-id=btn-label]]:leading-[1.125rem]` class once rotki/ui-library#515 lands — tightens the list-variant label line-box (20px) to match the md icon box (18px) so the text visually centers with the icon instead of sitting in the upper portion. -->
          <RuiButton
            variant="list"
            data-cy="settings-button"
            class="[&_[data-id=btn-label]]:leading-[1.125rem]"
            @click="navigate()"
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
          class="[&_[data-id=btn-label]]:leading-[1.125rem]"
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
          class="[&_[data-id=btn-label]]:leading-[1.125rem]"
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

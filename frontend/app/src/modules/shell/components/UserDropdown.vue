<script setup lang="ts">
import type { ConfirmQuestion } from '@/modules/shell/components/confirm-question';
import { externalLinks } from '@shared/external-links';
import { startPromise } from '@shared/utils';
import { useLogout } from '@/modules/auth/use-logout';
import { useSessionAuthStore } from '@/modules/auth/use-session-auth-store';
import { usePremiumHelper } from '@/modules/premium/use-premium-helper';
import { usePrivacyMode } from '@/modules/settings/use-privacy';
import ConfirmMenu from '@/modules/shell/components/ConfirmMenu.vue';
import ExternalLink from '@/modules/shell/components/ExternalLink.vue';
import MenuTooltipButton from '@/modules/shell/components/MenuTooltipButton.vue';
import ThemeControl from '@/modules/shell/theme/ThemeControl.vue';

const { t } = useI18n({ useScope: 'global' });

const { logout } = useLogout();
const { username } = storeToRefs(useSessionAuthStore());
const { privacyModeIcon, togglePrivacyMode } = usePrivacyMode();
const { isXs } = useBreakpoint();
const { currentTier, premium } = usePremiumHelper();

const tierLabel = computed<string>(() => {
  const tier = get(currentTier);
  return tier ? t('premium_placeholder.current_plan', { tier }) : '';
});

const logoutQuestion = computed<ConfirmQuestion>(() => ({
  confirmLabel: t('user_dropdown.logout'),
  message: t('user_dropdown.confirmation.message'),
}));

function acceptLogout(): void {
  startPromise(logout(true, { forgetSavedPassword: true }));
}

const { isDark } = useRotkiTheme();
</script>

<template>
  <div>
    <ConfirmMenu
      data-testid="user-menu"
      menu-class="min-w-40 max-w-88"
      close-on-content-click
    >
      <template #activator="{ attrs }">
        <MenuTooltipButton
          tooltip="Account"
          data-testid="user-menu-button"
          v-bind="attrs"
        >
          <RuiIcon name="lu-circle-user" />
        </MenuTooltipButton>
      </template>
      <template #default="{ ask }">
        <div data-testid="user-dropdown">
          <div class="py-3 flex flex-col items-center gap-1">
            <div
              data-testid="username"
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
                class="cursor-pointer!"
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
            <RuiButton
              variant="list"
              data-testid="settings-button"
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
            data-testid="privacy-mode-button"
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
            data-testid="theme-control"
          >
            {{ t('user_dropdown.switch_theme') }}
          </ThemeControl>
          <RuiDivider />
          <RuiButton
            variant="list"
            data-testid="logout-button"
            @click="ask(logoutQuestion, acceptLogout)"
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
      </template>
    </ConfirmMenu>
  </div>
</template>

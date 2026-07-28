import type { Ref } from 'vue';
import { once } from 'es-toolkit';
import { useFrontendSettingsWriter } from '@/modules/settings/use-frontend-settings-writer';
import { useSetting } from '@/modules/settings/use-setting';

export interface UseSilentNotificationsReturn {
  silent: Readonly<Ref<boolean>>;
  toggle: () => Promise<void>;
}

/**
 * Silent mode: nothing interrupts with a popup, everything still lands in the notification area
 * with its actions intact.
 *
 * It is an account-wide frontend setting rather than a session flag, so it follows the user
 * between logins and machines instead of quietly turning itself back on.
 *
 * ⚠️ The settings stores are resolved on first read, not at construction. This composable is built
 * by the notification dispatcher, which is itself built wherever notifications are used - including
 * contexts that never set up a pinia. Resolving up front makes those blow up with "no active
 * Pinia" without ever having sent a notification.
 *
 * Writes go through `useFrontendSettingsWriter` rather than `useSettingsOperations`, since the read
 * side is consumed by the dispatcher and routing it through the notification surface would close a
 * cycle back onto notifications.
 */
export function useSilentNotifications(): UseSilentNotificationsReturn {
  const settings = once(() => ({
    setting: useSetting('silentNotifications'),
    updateFrontendSetting: useFrontendSettingsWriter().updateFrontendSetting,
  }));

  const silent = computed<boolean>(() => get(settings().setting));

  async function toggle(): Promise<void> {
    await settings().updateFrontendSetting({ silentNotifications: !get(silent) });
  }

  return { silent, toggle };
}

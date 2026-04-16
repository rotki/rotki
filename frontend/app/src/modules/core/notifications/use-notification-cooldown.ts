import { useSessionStorage } from '@vueuse/core';

const NOTIFICATION_COOLDOWN_MS = 60_000;

export interface UseNotificationCooldownReturn {
  shouldSuppress: (group: string) => boolean;
  recordDisplay: (group: string) => void;
}

export function useNotificationCooldown(): UseNotificationCooldownReturn {
  const lastDisplay: Ref<Record<string, number>> = useSessionStorage('rotki.notification.last_display', {});

  function shouldSuppress(group: string): boolean {
    const lastTime = get(lastDisplay)[group] ?? 0;
    return Date.now() - lastTime < NOTIFICATION_COOLDOWN_MS;
  }

  function recordDisplay(group: string): void {
    set(lastDisplay, {
      ...get(lastDisplay),
      [group]: Date.now(),
    });
  }

  return { recordDisplay, shouldSuppress };
}

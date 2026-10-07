import type { EffectScope } from 'vue';
import { afterEach, assert, beforeEach, describe, expect, it, vi } from 'vitest';
import { endSession } from '@/modules/core/session/session-lifecycle';
import { SupportedLanguage } from '@/modules/settings/types/frontend-settings';

vi.mock('@/i18n', () => ({
  loadLocaleMessages: vi.fn(),
}));

const LAST_LANGUAGE_KEY = 'rotki.last_language';

let scope: EffectScope | undefined;

/**
 * Imports the composable into a fresh module registry, inside a scope the test stops.
 *
 * @remarks
 * `useLocale` is a `createSharedComposable` singleton, so without the reset one test's watchers
 * would still be running in the next.
 */
async function setup(): Promise<ReturnType<typeof import('@/modules/session/use-locale')['useLocale']>> {
  vi.resetModules();
  const { useLocale } = await import('@/modules/session/use-locale');
  scope = effectScope();
  const result = scope.run(() => useLocale());
  assert(result);
  return result;
}

async function setLanguageSetting(language: SupportedLanguage): Promise<void> {
  const { useSettingsRepo } = await import('@/modules/settings/settings-repo');
  useSettingsRepo().updateFrontend({ language });
  await nextTick();
}

function lastLanguage(): string | null {
  return localStorage.getItem(LAST_LANGUAGE_KEY);
}

describe('modules/session/use-locale', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    localStorage.clear();
  });

  afterEach(() => {
    scope?.stop();
  });

  it('should remember the language the user picks during a session for the login screen', async () => {
    await setup();

    await setLanguageSetting(SupportedLanguage.ES);

    expect(lastLanguage()).toBe(SupportedLanguage.ES);
  });

  it('should keep the remembered language when the logout reset restores the default', async () => {
    await setup();
    await setLanguageSetting(SupportedLanguage.ES);

    endSession();
    await setLanguageSetting(SupportedLanguage.EN);

    expect(lastLanguage()).toBe(SupportedLanguage.ES);
  });

  it('should remember English once the user stops following the machine language, with no session live', async () => {
    const { forceUpdateMachineLanguage } = await setup();
    await setLanguageSetting(SupportedLanguage.ES);

    endSession();
    set(forceUpdateMachineLanguage, 'false');
    await nextTick();

    expect(lastLanguage()).toBe(SupportedLanguage.EN);
  });
});

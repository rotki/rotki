<script setup lang="ts">
import type { SystemVersion } from '@shared/ipc';
import type { WebVersion } from '@/types';
import { millisecondsToSeconds } from '@/modules/core/common/data/date';
import { useMainStore } from '@/modules/core/common/use-main-store';
import { usePremium } from '@/modules/premium/use-premium';
import { useInterop } from '@/modules/shell/app/use-electron-interop';
import AboutDataDirectory from '@/modules/shell/components/AboutDataDirectory.vue';
import AppUpdateIndicator from '@/modules/shell/components/AppUpdateIndicator.vue';
import DateDisplay from '@/modules/shell/components/display/DateDisplay.vue';
import ExternalLink from '@/modules/shell/components/ExternalLink.vue';
import RotkiLogo from '@/modules/shell/components/RotkiLogo.vue';
import { isWebVersion, useVersionText } from '@/modules/shell/components/use-version-text';

const store = useMainStore();
const { isPackaged, openPath, version: getVersion } = useInterop();
const { t } = useI18n({ useScope: 'global' });

const { dataDirectory, version } = toRefs(store);
const versionInfo = asyncComputed<SystemVersion | WebVersion>(() => getVersion());

const premium = usePremium();
const componentsVersion = computed(() => {
  if (!get(premium))
    return null;

  const cmp = window.PremiumComponents;
  if (!cmp)
    return null;

  return {
    build: cmp.build,
    version: cmp.version,
  };
});

const webVersion = computed<WebVersion | null>(() => {
  const info = get(versionInfo);
  return info && isWebVersion(info) ? info : null;
});

const electronVersion = computed<SystemVersion | null>(() => {
  const info = get(versionInfo);
  return info && !isWebVersion(info) ? info : null;
});

const frontendVersion = __APP_VERSION__;

const versionText = useVersionText(() => ({
  appVersion: get(version).version,
  components: get(componentsVersion) ?? undefined,
  frontendVersion,
  system: get(versionInfo) ?? undefined,
}));

const { copy } = useClipboard({ source: versionText });
</script>

<template>
  <RuiCard
    variant="flat"
    class="overflow-hidden"
  >
    <template #custom-header>
      <div class="p-6 bg-rui-primary text-white">
        <RotkiLogo unique-key="00" />
        <h4 class="text-h4">
          {{ t('app.name') }}
        </h4>
        <span class="text-body-1">
          {{ t('app.moto') }}
        </span>
      </div>
    </template>
    <div class="flex items-center justify-between py-2">
      <div class="flex items-center flex-wrap gap-x-4">
        <div class="font-bold">
          {{ version.version }}
        </div>
        <ExternalLink
          :url="`https://github.com/rotki/rotki/releases/tag/v${version.version}`"
          :text="t('about.release_notes')"
        />
      </div>
      <AppUpdateIndicator />
    </div>
    <div class="border-t border-default mt-3 pt-4">
      <table class="w-full">
        <tbody>
          <tr>
            <td class="font-medium py-0.5 min-w-[150px]">
              {{ t('about.data_directory') }}
            </td>
            <td>
              <AboutDataDirectory
                :data-directory="dataDirectory"
                :is-packaged="isPackaged"
                @open-path="openPath(dataDirectory)"
              />
            </td>
          </tr>
          <tr>
            <td class="font-medium py-0.5 min-w-[150px]">
              {{ t('about.frontend_version') }}
            </td>
            <td class="text-rui-text-secondary">
              {{ frontendVersion }}
            </td>
          </tr>
          <template v-if="webVersion">
            <tr data-testid="about-web-platform">
              <td class="font-medium py-0.5 min-w-[150px]">
                {{ t('about.platform') }}
              </td>
              <td class="text-rui-text-secondary">
                {{ webVersion.platform }}
              </td>
            </tr>
            <tr data-testid="about-user-agent">
              <td class="font-medium py-0.5 min-w-[150px]">
                {{ t('about.user_agent') }}
              </td>
              <td class="text-rui-text-secondary">
                {{ webVersion.userAgent }}
              </td>
            </tr>
          </template>
          <template v-if="electronVersion">
            <tr data-testid="about-electron-platform">
              <td class="font-medium py-0.5 min-w-[150px]">
                {{ t('about.platform') }}
              </td>
              <td class="text-rui-text-secondary">
                {{ electronVersion.os }} {{ electronVersion.arch }}
                {{ electronVersion.osVersion }}
              </td>
            </tr>
            <tr data-testid="about-electron-version">
              <td class="font-medium py-0.5 min-w-[150px]">
                {{ t('about.electron') }}
              </td>
              <td class="text-rui-text-secondary">
                {{ electronVersion.electron }}
              </td>
            </tr>
          </template>
          <template v-if="componentsVersion">
            <tr>
              <td colspan="2">
                <div class="border-t border-default mt-4 pt-4 font-bold mb-2">
                  {{ t('about.components.title') }}
                </div>
              </td>
            </tr>
            <tr
              v-if="componentsVersion.version"
              data-testid="about-components-version"
            >
              <td class="font-medium py-0.5 min-w-[150px]">
                {{ t('about.components.version') }}
              </td>
              <td class="text-rui-text-secondary">
                {{ componentsVersion.version }}
              </td>
            </tr>
            <tr
              v-if="componentsVersion.build"
              data-testid="about-components-build"
            >
              <td class="font-medium py-0.5 min-w-[150px]">
                {{ t('about.components.build') }}
              </td>
              <td class="text-rui-text-secondary">
                <DateDisplay :timestamp="millisecondsToSeconds(componentsVersion.build)" />
              </td>
            </tr>
          </template>
        </tbody>
      </table>
    </div>
    <template #footer>
      <div class="flex justify-end w-full">
        <RuiButton
          color="primary"
          data-testid="about-copy"
          @click="copy()"
        >
          <template #prepend>
            <RuiIcon
              size="20"
              name="lu-copy"
            />
          </template>
          {{ t('about.copy_information_tooltip') }}
        </RuiButton>
      </div>
    </template>
  </RuiCard>
</template>

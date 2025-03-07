<script setup lang="ts">
import type { WebVersion } from '@/types';
import type { SystemVersion } from '@shared/ipc';
import RotkiLogo from '@/components/common/RotkiLogo.vue';
import DateDisplay from '@/components/display/DateDisplay.vue';
import CopyButton from '@/components/helper/CopyButton.vue';
import ExternalLink from '@/components/helper/ExternalLink.vue';
import AppUpdateIndicator from '@/components/status/AppUpdateIndicator.vue';
import { useInterop } from '@/composables/electron-interop';
import { usePremium } from '@/composables/premium';
import { useMainStore } from '@/store/main';

const store = useMainStore();
const { isPackaged, openPath, version: getVersion } = useInterop();
const { t } = useI18n();

const { dataDirectory, version } = toRefs(store);
const versionInfo = asyncComputed<SystemVersion | WebVersion>(() => getVersion());

const premium = usePremium();
const componentsVersion = computed(() => {
  if (!get(premium))
    return null;

  // @ts-expect-error components are not typed
  const cmp = window.PremiumComponents;
  if (!cmp)
    return null;

  return {
    build: cmp.build as number,
    version: cmp.version as string,
  };
});

const webVersion = computed<WebVersion | null>(() => {
  const info = get(versionInfo);
  if (!info || !('userAgent' in info))
    return null;

  return info;
});

const electronVersion = computed<SystemVersion | null>(() => {
  const info = get(versionInfo);
  if (!info || 'userAgent' in info)
    return null;

  return info;
});

const frontendVersion = __APP_VERSION__;

const versionText = computed(() => {
  const appVersion = t('about.app_version');
  const frontendVersion = t('about.frontend_version');
  let versionText = '';
  versionText += `${appVersion} ${get(version).version}\r\n`;
  versionText += `${frontendVersion} ${frontendVersion}\r\n`;

  const web = get(webVersion);
  const app = get(electronVersion);

  const platform = t('about.platform');

  if (web) {
    const userAgent = t('about.user_agent');
    versionText += `${platform} ${web.platform}\r\n`;
    versionText += `${userAgent} ${web.userAgent}\r\n`;
  }
  else if (app) {
    const electron = t('about.electron');
    versionText += `${platform} ${app.os} ${app.arch} ${app.osVersion}\r\n`;
    versionText += `${electron} ${app.electron}\r\n`;
  }

  if (get(premium)) {
    const cmp = get(componentsVersion);
    if (cmp) {
      const cmpVersion = t('about.components.version');
      const cmpBuild = t('about.components.build');

      versionText += `${cmpVersion} ${cmp.version}\r\n`;
      versionText += `${cmpBuild} ${cmp.build}\r\n`;
    }
  }

  return versionText;
});

const { copy } = useClipboard({ source: versionText });
</script>

<template>
  <RuiCard
    variant="flat"
    class="overflow-hidden"
  >
    <template #custom-header>
      <div class="p-6 bg-rui-primary text-white">
        <RotkiLogo
          logo="about"
          unique-key="00"
        />
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
            <td :class="$style.label">
              {{ t('about.data_directory') }}
            </td>
            <td>
              <div class="flex items-center justify-between">
                <RuiTooltip
                  :popper="{ placement: 'top' }"
                  :open-delay="400"
                >
                  <template #activator>
                    <div
                      class="truncate text-rui-text-secondary"
                      :class="$style.directory"
                    >
                      {{ dataDirectory }}
                    </div>
                  </template>
                  <span :class="$style.directory">
                    {{ dataDirectory }}
                  </span>
                </RuiTooltip>
                <div
                  v-if="isPackaged"
                  class="ml-2"
                >
                  <RuiTooltip
                    :popper="{ placement: 'top' }"
                    :open-delay="400"
                  >
                    <template #activator>
                      <RuiButton
                        icon
                        size="sm"
                        variant="text"
                        @click="openPath(dataDirectory)"
                      >
                        <RuiIcon
                          size="18"
                          name="lu-folder-open"
                        />
                      </RuiButton>
                    </template>
                    <span>{{ t('about.open_data_dir_tooltip') }}</span>
                  </RuiTooltip>
                </div>
                <div v-else>
                  <CopyButton
                    size="sm"
                    :value="dataDirectory"
                    :tooltip="t('about.copy_data_directory_tooltip')"
                  />
                </div>
              </div>
            </td>
          </tr>
          <tr>
            <td :class="$style.label">
              {{ t('about.frontend_version') }}
            </td>
            <td class="text-rui-text-secondary">
              {{ frontendVersion }}
            </td>
          </tr>
          <template v-if="webVersion">
            <tr>
              <td :class="$style.label">
                {{ t('about.platform') }}
              </td>
              <td class="text-rui-text-secondary">
                {{ webVersion.platform }}
              </td>
            </tr>
            <tr>
              <td :class="$style.label">
                {{ t('about.user_agent') }}
              </td>
              <td class="text-rui-text-secondary">
                {{ webVersion.userAgent }}
              </td>
            </tr>
          </template>
          <template v-if="electronVersion">
            <tr>
              <td :class="$style.label">
                {{ t('about.platform') }}
              </td>
              <td class="text-rui-text-secondary">
                {{ electronVersion.os }} {{ electronVersion.arch }}
                {{ electronVersion.osVersion }}
              </td>
            </tr>
            <tr>
              <td :class="$style.label">
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
            <tr v-if="componentsVersion.version">
              <td :class="$style.label">
                {{ t('about.components.version') }}
              </td>
              <td class="text-rui-text-secondary">
                {{ componentsVersion.version }}
              </td>
            </tr>
            <tr v-if="componentsVersion.build">
              <td :class="$style.label">
                {{ t('about.components.build') }}
              </td>
              <td class="text-rui-text-secondary">
                <DateDisplay :timestamp="componentsVersion.build / 1000" />
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

<style module lang="scss">
.label {
  @apply font-medium py-0.5;
  min-width: 150px;
}

.directory {
  max-width: 280px;
}
</style>

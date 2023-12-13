<script setup lang="ts">
import { type SystemVersion } from '@/electron-main/ipc';
import { type WebVersion } from '@/types';

const css = useCssModule();

const store = useMainStore();
const { version: getVersion, isPackaged, openPath } = useInterop();
const { t } = useI18n();

const { version, dataDirectory } = toRefs(store);
const versionInfo = asyncComputed<SystemVersion | WebVersion>(() =>
  getVersion()
);

const premium = usePremium();
const componentsVersion = computed(() => {
  if (!get(premium)) {
    return null;
  }

  // @ts-ignore
  const cmp = window.PremiumComponents;
  if (!cmp) {
    return null;
  }
  return {
    version: cmp.version as string,
    build: cmp.build as number
  };
});

const webVersion = computed<WebVersion | null>(() => {
  const info = get(versionInfo);
  if (!info || !('userAgent' in info)) {
    return null;
  }
  return info;
});

const electronVersion = computed<SystemVersion | null>(() => {
  const info = get(versionInfo);
  if (!info || 'userAgent' in info) {
    return null;
  }
  return info;
});

// eslint-disable-next-line no-undef
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
  } else if (app) {
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

const remoteAboutLogo =
  'https://raw.githubusercontent.com/rotki/data/main/assets/icons/about_logo.png';

const { copy } = useClipboard({ source: versionText });
</script>

<template>
  <!-- TODO: Remove bg class when https://github.com/rotki/ui-library/issues/124 is resolved -->
  <RuiCard variant="flat" class="dark:bg-[#1E1E1E]">
    <template #custom-header>
      <div class="p-6 bg-rui-primary text-white">
        <RuiLogo :custom-src="remoteAboutLogo" />
        <h4 class="text-h4">{{ t('app.name') }}</h4>
        <span class="text-body-1">
          {{ t('app.moto') }}
        </span>
      </div>
    </template>
    <div class="flex items-center justify-between" :class="css.version">
      <div class="flex items-center">
        <div class="font-bold">{{ version.version }}</div>
        <div class="ml-4">
          <ExternalLink
            :url="`https://github.com/rotki/rotki/releases/tag/v${version.version}`"
            :text="t('about.release_notes')"
          />
        </div>
      </div>
      <AppUpdateIndicator />
    </div>
    <div class="border-t border-default mt-3 pt-4">
      <table class="w-full">
        <tbody>
          <tr>
            <td :class="css.label">
              {{ t('about.data_directory') }}
            </td>
            <td>
              <div class="flex flex-row justify-between">
                <RuiTooltip :popper="{ placement: 'top' }" :open-delay="400">
                  <template #activator>
                    <div
                      class="text-truncate text-rui-text-secondary"
                      :class="css.directory"
                    >
                      {{ dataDirectory }}
                    </div>
                  </template>
                  <span :class="css.directory">
                    {{ dataDirectory }}
                  </span>
                </RuiTooltip>
                <div v-if="isPackaged" class="ml-2">
                  <RuiTooltip :popper="{ placement: 'top' }" :open-delay="400">
                    <template #activator>
                      <RuiButton
                        icon
                        size="sm"
                        variant="text"
                        @click="openPath(dataDirectory)"
                      >
                        <RuiIcon size="18" name="folder-open-line" />
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
            <td :class="css.label">
              {{ t('about.frontend_version') }}
            </td>
            <td class="text-rui-text-secondary">
              {{ frontendVersion }}
            </td>
          </tr>
          <template v-if="webVersion">
            <tr>
              <td :class="css.label">
                {{ t('about.platform') }}
              </td>
              <td class="text-rui-text-secondary">
                {{ webVersion.platform }}
              </td>
            </tr>
            <tr>
              <td :class="css.label">
                {{ t('about.user_agent') }}
              </td>
              <td class="text-rui-text-secondary">
                {{ webVersion.userAgent }}
              </td>
            </tr>
          </template>
          <template v-if="electronVersion">
            <tr>
              <td :class="css.label">
                {{ t('about.platform') }}
              </td>
              <td class="text-rui-text-secondary">
                {{ electronVersion.os }} {{ electronVersion.arch }}
                {{ electronVersion.osVersion }}
              </td>
            </tr>
            <tr>
              <td :class="css.label">
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
              <td :class="css.label">
                {{ t('about.components.version') }}
              </td>
              <td class="text-rui-text-secondary">
                {{ componentsVersion.version }}
              </td>
            </tr>
            <tr v-if="componentsVersion.build">
              <td :class="css.label">
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
      <div class="p-3 flex justify-end w-full">
        <RuiButton color="primary" @click="copy()">
          <template #prepend>
            <RuiIcon size="20" name="file-copy-line" />
          </template>
          {{ t('about.copy_information_tooltip') }}
        </RuiButton>
      </div>
    </template>
  </RuiCard>
</template>

<style module lang="scss">
.version {
  height: 36px;
}

.label {
  min-width: 130px;
  @apply font-medium py-0.5;
}

.directory {
  max-width: 200px;
}
</style>

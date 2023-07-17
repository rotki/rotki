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
</script>

<template>
  <VCard class="pb-6" width="500px" light :class="css.about">
    <div class="pt-6 pb-3 text-h2 font-weight-black white--text primary">
      <span class="px-6">{{ t('app.name') }}</span>
      <span class="d-block mb-3 pl-6 text-caption">
        {{ t('app.moto') }}
      </span>
    </div>
    <VCardText>
      <div class="mt-4 mb-2">
        <RotkiLogo width="72px" :url="remoteAboutLogo" />
      </div>
      <div class="d-flex flex-row align-center mt-4" :class="css.version">
        <div class="font-weight-bold">{{ version.version }}</div>
        <div class="font-weight-regular ml-4">
          <BaseExternalLink
            :href="`https://github.com/rotki/rotki/releases/tag/v${version.version}`"
            :text="t('about.release_notes')"
          />
        </div>
        <VSpacer />
        <AppUpdateIndicator />
      </div>
      <VDivider class="mt-4 mb-2" />
      <VRow align="center">
        <VCol>
          <table class="fill-width">
            <tbody>
              <tr>
                <td class="font-weight-medium" :class="css.label">
                  {{ t('about.data_directory') }}
                </td>
                <td>
                  <div class="d-flex flex-row">
                    <VTooltip top open-delay="400">
                      <template #activator="{ on }">
                        <div
                          class="text-truncate"
                          :class="css.directory"
                          v-on="on"
                        >
                          {{ dataDirectory }}
                        </div>
                      </template>
                      <span :class="css.directory">
                        {{ dataDirectory }}
                      </span>
                    </VTooltip>
                    <VSpacer />
                    <div v-if="isPackaged" class="ml-2">
                      <VTooltip top open-delay="400">
                        <template #activator="{ on, attrs }">
                          <VBtn
                            v-bind="attrs"
                            icon
                            x-small
                            v-on="on"
                            @click="openPath(dataDirectory)"
                          >
                            <VIcon x-small>mdi-launch</VIcon>
                          </VBtn>
                        </template>
                        <span>{{ t('about.open_data_dir_tooltip') }}</span>
                      </VTooltip>
                    </div>
                    <div v-else>
                      <CopyButton
                        :value="dataDirectory"
                        :tooltip="t('about.copy_data_directory_tooltip')"
                      />
                    </div>
                  </div>
                </td>
              </tr>
              <tr>
                <td class="font-weight-medium" :class="css.label">
                  {{ t('about.frontend_version') }}
                </td>
                <td>
                  {{ frontendVersion }}
                </td>
              </tr>
              <tr v-if="webVersion">
                <td class="font-weight-medium" :class="css.label">
                  {{ t('about.platform') }}
                </td>
                <td>{{ webVersion.platform }}</td>
              </tr>
              <tr v-if="webVersion">
                <td class="font-weight-medium" :class="css.label">
                  {{ t('about.user_agent') }}
                </td>
                <td>{{ webVersion.userAgent }}</td>
              </tr>
              <tr v-if="electronVersion">
                <td class="font-weight-medium" :class="css.label">
                  {{ t('about.platform') }}
                </td>
                <td>
                  {{ electronVersion.os }} {{ electronVersion.arch }}
                  {{ electronVersion.osVersion }}
                </td>
              </tr>
              <tr v-if="electronVersion">
                <td class="font-weight-medium" :class="css.label">
                  {{ t('about.electron') }}
                </td>
                <td>
                  {{ electronVersion.electron }}
                </td>
              </tr>
              <tr v-if="componentsVersion">
                <td colspan="2">
                  <VDivider class="mt-4 mb-2" />
                  <div class="font-weight-bold mb-1">
                    {{ t('about.components.title') }}
                  </div>
                </td>
              </tr>
              <tr v-if="componentsVersion?.version">
                <td class="font-weight-medium" :class="css.label">
                  {{ t('about.components.version') }}
                </td>
                <td>{{ componentsVersion.version }}</td>
              </tr>
              <tr v-if="componentsVersion?.build">
                <td class="font-weight-medium" :class="css.label">
                  {{ t('about.components.build') }}
                </td>
                <td>
                  <DateDisplay :timestamp="componentsVersion.build / 1000" />
                </td>
              </tr>
            </tbody>
          </table>
        </VCol>
        <VCol cols="auto">
          <CopyButton
            :value="versionText"
            :tooltip="t('about.copy_information_tooltip')"
          />
        </VCol>
      </VRow>
    </VCardText>
  </VCard>
</template>

<style module lang="scss">
.version {
  height: 36px;
}

.label {
  min-width: 130px;
}

.directory {
  max-width: 200px;
}
</style>

<template>
  <v-card class="pb-6" width="500px" light :class="css.about">
    <div class="pt-6 pb-3 text-h2 font-weight-black white--text primary">
      <span class="px-6">{{ tc('app.name') }}</span>
      <span class="d-block mb-3 pl-6 text-caption">
        {{ tc('app.moto') }}
      </span>
    </div>
    <v-card-text>
      <v-img
        class="mt-4 mb-2"
        contain
        max-width="72px"
        src="/assets/images/rotkehlchen_no_text.png"
      />
      <div class="d-flex flex-row align-center mt-4" :class="css.version">
        <div class="font-weight-bold">{{ version.version }}</div>
        <div class="font-weight-regular ml-4">
          <base-external-link
            :href="`https://github.com/rotki/rotki/releases/tag/v${version.version}`"
            :text="tc('about.release_notes')"
          />
        </div>
        <v-spacer />
        <app-update-indicator />
      </div>
      <v-divider class="mt-4 mb-2" />
      <v-row align="center">
        <v-col>
          <table class="fill-width">
            <tbody>
              <tr>
                <td class="font-weight-medium" :class="css.label">
                  {{ tc('about.data_directory') }}
                </td>
                <td>
                  <div class="d-flex flex-row">
                    <v-tooltip top open-delay="400">
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
                    </v-tooltip>
                    <v-spacer />
                    <div v-if="isPackaged" class="ml-2">
                      <v-tooltip top open-delay="400">
                        <template #activator="{ on, attrs }">
                          <v-btn
                            v-bind="attrs"
                            icon
                            x-small
                            v-on="on"
                            @click="openPath(dataDirectory)"
                          >
                            <v-icon x-small>mdi-launch</v-icon>
                          </v-btn>
                        </template>
                        <span>{{ tc('about.open_data_dir_tooltip') }}</span>
                      </v-tooltip>
                    </div>
                    <div v-else>
                      <copy-button
                        :value="dataDirectory"
                        :tooltip="tc('about.copy_data_directory_tooltip')"
                      />
                    </div>
                  </div>
                </td>
              </tr>
              <tr>
                <td class="font-weight-medium" :class="css.label">
                  {{ tc('about.frontend_version') }}
                </td>
                <td>
                  {{ frontendVersion }}
                </td>
              </tr>
              <tr v-if="webVersion">
                <td class="font-weight-medium" :class="css.label">
                  {{ tc('about.platform') }}
                </td>
                <td>{{ webVersion.platform }}</td>
              </tr>
              <tr v-if="webVersion">
                <td class="font-weight-medium" :class="css.label">
                  {{ tc('about.user_agent') }}
                </td>
                <td>{{ webVersion.userAgent }}</td>
              </tr>
              <tr v-if="electronVersion">
                <td class="font-weight-medium" :class="css.label">
                  {{ tc('about.platform') }}
                </td>
                <td>
                  {{ electronVersion.os }} {{ electronVersion.arch }}
                  {{ electronVersion.osVersion }}
                </td>
              </tr>
              <tr v-if="electronVersion">
                <td class="font-weight-medium" :class="css.label">
                  {{ tc('about.electron') }}
                </td>
                <td>
                  {{ electronVersion.electron }}
                </td>
              </tr>
              <tr v-if="componentsVersion">
                <td colspan="2">
                  <v-divider class="mt-4 mb-2" />
                  <div class="font-weight-bold mb-1">
                    {{ tc('about.components.title') }}
                  </div>
                </td>
              </tr>
              <tr v-if="componentsVersion?.version">
                <td class="font-weight-medium" :class="css.label">
                  {{ tc('about.components.version') }}
                </td>
                <td>{{ componentsVersion.version }}</td>
              </tr>
              <tr v-if="componentsVersion?.build">
                <td class="font-weight-medium" :class="css.label">
                  {{ tc('about.components.build') }}
                </td>
                <td>
                  <date-display :timestamp="componentsVersion.build / 1000" />
                </td>
              </tr>
            </tbody>
          </table>
        </v-col>
        <v-col cols="auto">
          <copy-button
            :value="versionText"
            :tooltip="tc('about.copy_information_tooltip')"
          />
        </v-col>
      </v-row>
    </v-card-text>
  </v-card>
</template>

<script setup lang="ts">
import BaseExternalLink from '@/components/base/BaseExternalLink.vue';
import AppUpdateIndicator from '@/components/status/AppUpdateIndicator.vue';
import { usePremium } from '@/composables/premium';
import { useInterop } from '@/electron-interop';
import { SystemVersion } from '@/electron-main/ipc';
import { useMainStore } from '@/store/main';
import { WebVersion } from '@/types';

const css = useCssModule();

const store = useMainStore();
const { version: getVersion, isPackaged, openPath } = useInterop();
const { tc } = useI18n();

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
  const appVersion = tc('about.app_version');
  const frontendVersion = tc('about.frontend_version');
  let versionText = '';
  versionText += `${appVersion} ${get(version).version}\r\n`;
  versionText += `${frontendVersion} ${frontendVersion}\r\n`;

  const web = get(webVersion);
  const app = get(electronVersion);

  const platform = tc('about.platform');

  if (web) {
    const userAgent = tc('about.user_agent');
    versionText += `${platform} ${web.platform}\r\n`;
    versionText += `${userAgent} ${web.userAgent}\r\n`;
  } else if (app) {
    const electron = tc('about.electron');
    versionText += `${platform} ${app.os} ${app.arch} ${app.osVersion}\r\n`;
    versionText += `${electron} ${app.electron}\r\n`;
  }

  if (get(premium)) {
    const cmp = get(componentsVersion);
    if (cmp) {
      const cmpVersion = tc('about.components.version');
      const cmpBuild = tc('about.components.build');

      versionText += `${cmpVersion} ${cmp.version}\r\n`;
      versionText += `${cmpBuild} ${cmp.build}\r\n`;
    }
  }

  return versionText;
});
</script>

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

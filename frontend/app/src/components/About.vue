<template>
  <v-card class="about pb-6" width="500px" light>
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
      <div class="d-flex flex-row align-center about__version mt-4">
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
      <div class="d-flex flex-row align-center">
        <div class="font-weight-medium about__label">
          {{ tc('about.data_directory') }}
        </div>
        <div class="text-truncate">{{ dataDirectory }}</div>
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
      </div>
      <v-row align="center">
        <v-col>
          <div class="d-flex flex-row">
            <div class="font-weight-medium about__label">
              {{ tc('about.frontend_version') }}
            </div>
            <div>{{ frontendVersion }}</div>
          </div>

          <div v-if="webVersion">
            <div class="d-flex flex-row">
              <div class="font-weight-medium about__label">
                {{ tc('about.platform') }}
              </div>
              <div>{{ webVersion.platform }}</div>
            </div>
            <div class="d-flex flex-row">
              <div class="font-weight-medium about__label">
                {{ tc('about.user_agent') }}
              </div>
              <div>{{ webVersion.userAgent }}</div>
            </div>
          </div>
          <div v-else-if="electronVersion">
            <div class="d-flex flex-row">
              <div class="font-weight-medium about__label">
                {{ tc('about.platform') }}
              </div>
              <div>
                {{ electronVersion.os }} {{ electronVersion.arch }}
                {{ electronVersion.osVersion }}
              </div>
            </div>
            <div class="d-flex flex-row">
              <div class="font-weight-medium about__label">
                {{ tc('about.electron') }}
              </div>
              <div>{{ electronVersion.electron }}</div>
            </div>
          </div>
        </v-col>
        <v-col cols="auto">
          <v-tooltip open-delay="400" top>
            <template #activator="{ on, attrs }">
              <v-btn icon v-bind="attrs" v-on="on" @click="copy">
                <v-icon>mdi-content-copy</v-icon>
              </v-btn>
            </template>
            <span>{{ tc('about.copy_tooltip') }}</span>
          </v-tooltip>
        </v-col>
      </v-row>
    </v-card-text>
  </v-card>
</template>

<script lang="ts">
import { computed, defineComponent, toRefs } from '@vue/composition-api';
import { asyncComputed, get, useClipboard } from '@vueuse/core';
import { useI18n } from 'vue-i18n-composable';
import BaseExternalLink from '@/components/base/BaseExternalLink.vue';
import AppUpdateIndicator from '@/components/status/AppUpdateIndicator.vue';
import { useInterop } from '@/electron-interop';
import { SystemVersion } from '@/electron-main/ipc';
import { useMainStore } from '@/store/main';
import { WebVersion } from '@/types';

export default defineComponent({
  name: 'About',
  components: { AppUpdateIndicator, BaseExternalLink },
  setup() {
    const store = useMainStore();
    const { version: getVersion, isPackaged, openPath } = useInterop();
    const { tc } = useI18n();

    const { version, dataDirectory } = toRefs(store);
    const versionInfo = asyncComputed<SystemVersion | WebVersion>(() =>
      getVersion()
    );

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

    const copy = () => {
      let versionText = '';
      versionText += `App Version: ${get(version).version}\r\n`;
      versionText += `Frontend Version: ${frontendVersion}\r\n`;

      const web = get(webVersion);
      const app = get(electronVersion);

      if (web) {
        versionText += `Platform: ${web.platform}\r\n`;
        versionText += `User Agent: ${web.userAgent}\r\n`;
      } else if (app) {
        versionText += `Platform: ${app.os} ${app.arch} ${app.osVersion}\r\n`;
        versionText += `Electron: ${app.electron}\r\n`;
      }

      const { copy } = useClipboard({ source: versionText });
      copy();
    };

    return {
      webVersion,
      electronVersion,
      version,
      dataDirectory,
      frontendVersion,
      isPackaged,
      tc,
      copy,
      openPath
    };
  }
});
</script>

<style scoped lang="scss">
.about {
  &__version {
    height: 36px;
  }

  &__label {
    min-width: 120px;
  }
}
</style>

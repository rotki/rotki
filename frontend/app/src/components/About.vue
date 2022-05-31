<template>
  <v-card class="about pb-6" width="500px" light>
    <div class="pt-6 pb-3 text-h2 font-weight-black white--text primary">
      <span class="px-6">{{ $t('app.name') }}</span>
      <span class="d-block mb-3 pl-6 text-caption">
        {{ $t('app.moto') }}
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
            :text="$t('about.release_notes')"
          />
        </div>
        <v-spacer />
        <app-update-indicator />
      </div>
      <v-divider class="mt-4 mb-2" />
      <div class="d-flex flex-row align-center">
        <div class="font-weight-medium about__label">
          {{ $t('about.data_directory') }}
        </div>
        <div class="text-truncate">{{ dataDirectory }}</div>
        <v-spacer />
        <div v-if="$interop.isPackaged" class="ml-2">
          <v-tooltip top open-delay="400">
            <template #activator="{ on, attrs }">
              <v-btn
                v-bind="attrs"
                icon
                x-small
                v-on="on"
                @click="$interop.openPath(dataDirectory)"
              >
                <v-icon x-small>mdi-launch</v-icon>
              </v-btn>
            </template>
            <span>{{ $t('about.open_data_dir_tooltip') }}</span>
          </v-tooltip>
        </div>
      </div>
      <v-row align="center">
        <v-col>
          <div class="d-flex flex-row">
            <div class="font-weight-medium about__label">
              {{ $t('about.frontend_version') }}
            </div>
            <div>{{ frontendVersion }}</div>
          </div>

          <div v-if="web">
            <div class="d-flex flex-row">
              <div class="font-weight-medium about__label">
                {{ $t('about.platform') }}
              </div>
              <div>{{ versionInfo.platform }}</div>
            </div>
            <div class="d-flex flex-row">
              <div class="font-weight-medium about__label">
                {{ $t('about.user_agent') }}
              </div>
              <div>{{ versionInfo.userAgent }}</div>
            </div>
          </div>
          <div v-else-if="versionInfo">
            <div class="d-flex flex-row">
              <div class="font-weight-medium about__label">
                {{ $t('about.platform') }}
              </div>
              <div>
                {{ versionInfo.os }} {{ versionInfo.arch }}
                {{ versionInfo.osVersion }}
              </div>
            </div>
            <div class="d-flex flex-row">
              <div class="font-weight-medium about__label">
                {{ $t('about.electron') }}
              </div>
              <div>{{ versionInfo.electron }}</div>
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
            <span>{{ $t('about.copy_tooltip') }}</span>
          </v-tooltip>
        </v-col>
      </v-row>
    </v-card-text>
  </v-card>
</template>

<script lang="ts">
import {
  computed,
  defineComponent,
  onMounted,
  ref,
  toRefs
} from '@vue/composition-api';
import { get, set, useClipboard } from '@vueuse/core';
import BaseExternalLink from '@/components/base/BaseExternalLink.vue';
import AppUpdateIndicator from '@/components/status/AppUpdateIndicator.vue';
import { interop } from '@/electron-interop';
import { SystemVersion } from '@/electron-main/ipc';
import { useMainStore } from '@/store/store';
import { WebVersion } from '@/types';

export default defineComponent({
  name: 'About',
  components: { AppUpdateIndicator, BaseExternalLink },
  setup() {
    const store = useMainStore();

    const { version, dataDirectory } = toRefs(store);
    const versionInfo = ref<SystemVersion | WebVersion | null>(null);

    const web = computed<boolean>(() => {
      return (get(versionInfo) && 'userAgent' in get(versionInfo)!) ?? false;
    });

    const frontendVersion = computed<string>(() => {
      return process.env.VERSION ?? '';
    });

    onMounted(async () => {
      set(versionInfo, await interop.version());
    });

    const copy = () => {
      let versionText = '';
      versionText += `App Version: ${get(version).version}\r\n`;
      versionText += `Frontend Version: ${get(frontendVersion)}\r\n`;
      const versionInfoVal = get(versionInfo);
      if (versionInfoVal) {
        if ('userAgent' in versionInfoVal) {
          versionText += `Platform: ${versionInfoVal.platform}\r\n`;
          versionText += `User Agent: ${versionInfoVal.userAgent}\r\n`;
        } else {
          versionText += `Platform: ${versionInfoVal.os} ${versionInfoVal.arch} ${versionInfoVal.osVersion}\r\n`;
          versionText += `Electron: ${versionInfoVal.electron}\r\n`;
        }
      }

      const { copy } = useClipboard({ source: versionText });
      copy();
    };

    return {
      version,
      copy,
      dataDirectory,
      versionInfo,
      web,
      frontendVersion
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

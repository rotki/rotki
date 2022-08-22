<template>
  <v-snackbar
    v-if="isPackaged"
    :value="showUpdatePopup"
    class="update-popup"
    :timeout="-1"
    light
    top
    multi-line
    vertical
    right
    app
    rounded
    width="380px"
  >
    <v-row v-if="!restarting" align="center">
      <v-col cols="auto">
        <v-icon v-if="error" large color="error">
          mdi-alert-circle-outline
        </v-icon>
        <v-icon
          v-else-if="!downloadReady && !downloading"
          large
          color="primary"
        >
          mdi-arrow-up-bold-circle
        </v-icon>
        <v-icon v-else large color="primary">mdi-arrow-down-bold-circle</v-icon>
      </v-col>
      <v-col class="text-body-1">
        <span v-if="error" class="error--text">
          {{ error }}
        </span>
        <span v-else-if="downloading">
          {{ $t('update_popup.download_progress') }}
        </span>
        <div v-else-if="!downloadReady">
          <i18n tag="div" path="update_popup.messages">
            <template #releaseNotes>
              <base-external-link
                :text="$t('update_popup.release_notes')"
                :href="releaseNotesLink"
              />
            </template>
          </i18n>
          <div>{{ $t('update_popup.download_nudge') }}</div>
        </div>
        <span v-else>{{ $t('update_popup.downloaded') }}</span>
      </v-col>
    </v-row>
    <v-row v-else align="center">
      <v-col cols="auto">
        <v-icon large color="primary"> mdi-spin mdi-loading </v-icon>
      </v-col>
      <v-col class="text-body-1">{{ $t('update_popup.restart') }}</v-col>
    </v-row>

    <v-progress-linear
      v-if="downloading"
      :value="percentage"
      class="mt-2"
      color="primary"
      height="25"
    >
      <template #default="{ value }">
        <strong class="white--text">
          {{ $t('update_popup.progress', { percentage: Math.ceil(value) }) }}
        </strong>
      </template>
    </v-progress-linear>

    <template v-if="error" #action="{ attrs }">
      <v-btn text v-bind="attrs" @click="dismiss">
        {{ $t('common.actions.dismiss') }}
      </v-btn>
    </template>
    <template v-else-if="!downloading && !restarting" #action="{ attrs }">
      <v-btn text v-bind="attrs" @click="dismiss">
        {{ $t('common.actions.cancel') }}
      </v-btn>
      <v-btn
        v-if="!downloadReady"
        color="primary"
        text
        v-bind="attrs"
        @click="update()"
      >
        {{ $t('common.actions.update') }}
      </v-btn>
      <v-btn v-else color="primary" text v-bind="attrs" @click="install()">
        {{ $t('common.actions.install') }}
      </v-btn>
    </template>
  </v-snackbar>
</template>

<script setup lang="ts">
import { set } from '@vueuse/core';
import { storeToRefs } from 'pinia';
import { onMounted, ref } from 'vue';
import BaseExternalLink from '@/components/base/BaseExternalLink.vue';
import { useInterop } from '@/electron-interop';
import { default as i18nFn } from '@/i18n';
import { useSessionStore } from '@/store/session';

const releaseNotesLink = 'https://github.com/rotki/rotki/releases';

const downloadReady = ref(false);
const downloading = ref(false);
const restarting = ref(false);
const percentage = ref(0);
const error = ref('');

const store = useSessionStore();
const { showUpdatePopup } = storeToRefs(store);
const { checkForUpdate } = store;
const { downloadUpdate, isPackaged, installUpdate } = useInterop();

const dismiss = () => {
  set(showUpdatePopup, false);
  setTimeout(() => {
    set(error, '');
    set(downloading, false);
    set(downloadReady, false);
    set(percentage, 0);
  }, 400);
};

const update = async () => {
  set(downloading, true);
  const downloaded = await downloadUpdate(progress => {
    set(percentage, progress);
  });
  set(downloading, false);
  if (downloaded) {
    set(downloadReady, true);
    set(showUpdatePopup, true);
  } else {
    set(error, i18nFn.t('update_popup.download_failed.message').toString());
  }
};

const install = async () => {
  set(downloadReady, false);
  set(restarting, true);

  const result = await installUpdate();
  if (typeof result !== 'boolean') {
    set(
      error,
      i18nFn
        .t('update_popup.install_failed.message', {
          message: result
        })
        .toString()
    );
  }
};

onMounted(async () => {
  if (isPackaged) {
    await checkForUpdate();
  }
});
</script>
<style scoped lang="scss">
.update-popup {
  ::v-deep {
    .v-snack {
      &__wrapper {
        margin: 16px;
        width: 400px;
        box-shadow: 0 2px 12px rgba(74, 91, 120, 0.1) !important;
      }
    }
  }
}
</style>

<template>
  <v-snackbar
    v-if="$interop.isPackaged"
    v-model="popup"
    class="update-popup"
    :timeout="-1"
    light
    top
    multi-line
    vertical
    right
    app
    rounded
    width="400px"
  >
    <v-row align="center">
      <v-col cols="auto">
        <v-icon v-if="!downloadReady" large color="primary">
          mdi-arrow-up-bold-circle
        </v-icon>
        <v-icon v-else large color="primary">mdi-arrow-down-circle</v-icon>
      </v-col>
      <v-col class="text-body-1">
        <span v-if="downloading">
          {{ $t('update_popup.download_progress') }}
        </span>
        <span v-else-if="!downloadReady">
          {{ $t('update_popup.messages') }}
        </span>
        <span v-else>{{ $t('update_popup.downloaded') }}</span>
      </v-col>
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

    <template v-if="!downloading" #action="{ attrs }">
      <v-btn text v-bind="attrs" @click="popup = false">
        {{ $t('update_popup.action.cancel') }}
      </v-btn>
      <v-btn
        v-if="!downloadReady"
        color="primary"
        text
        v-bind="attrs"
        @click="update()"
      >
        {{ $t('update_popup.action.update') }}
      </v-btn>
      <v-btn v-else color="primary" text v-bind="attrs" @click="install()">
        {{ $t('update_popup.action.install') }}
      </v-btn>
    </template>
  </v-snackbar>
</template>

<script lang="ts">
import { Component, Vue } from 'vue-property-decorator';
import { Interop } from '@/electron-main/ipc';
import { Severity } from '@/store/notifications/consts';
import { notify } from '@/store/notifications/utils';
import { assert } from '@/utils/assertions';

@Component({})
export default class UpdatePopup extends Vue {
  popup: boolean = false;
  downloadReady: boolean = false;
  downloading: boolean = false;
  percentage: number = 0;

  async update() {
    this.downloading = true;
    const downloaded = await this.interop.downloadUpdate(percentage => {
      this.percentage = percentage;
    });
    this.downloading = false;
    if (downloaded) {
      this.downloadReady = true;
      this.popup = true;
    } else {
      notify(
        this.$t('update_popup.download_failed.message').toString(),
        this.$t('update_popup.download_failed.title').toString(),
        Severity.ERROR,
        true
      );
    }
  }

  async install() {
    this.downloadReady = false;
    this.popup = false;
    const result = await this.interop.installUpdate();
    if (typeof result !== 'boolean') {
      notify(
        this.$t('update_popup.install_failed.message', {
          message: result
        }).toString(),
        this.$t('update_popup.install_failed.title').toString(),
        Severity.ERROR,
        true
      );
    }
  }

  get interop(): Interop {
    const interop = window.interop;
    assert(interop);
    return interop;
  }

  async created() {
    if (!this.$interop.isPackaged) {
      return;
    }
    this.popup = await this.interop.checkForUpdates();
  }
}
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

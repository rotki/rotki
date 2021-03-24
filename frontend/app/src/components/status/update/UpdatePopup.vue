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
        <span v-else-if="!downloadReady">
          {{ $t('update_popup.messages') }}
        </span>
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
        {{ $t('update_popup.action.dismiss') }}
      </v-btn>
    </template>
    <template v-else-if="!downloading && !restarting" #action="{ attrs }">
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
import { assert } from '@/utils/assertions';

@Component({})
export default class UpdatePopup extends Vue {
  popup: boolean = false;
  downloadReady: boolean = false;
  downloading: boolean = false;
  restarting: boolean = false;
  percentage: number = 0;
  error: string = '';

  dismiss() {
    this.popup = false;
    setTimeout(() => {
      this.error = '';
      this.downloading = false;
      this.downloadReady = false;
      this.percentage = 0;
    }, 400);
  }

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
      this.error = this.$t('update_popup.download_failed.message').toString();
    }
  }

  async install() {
    this.downloadReady = false;
    this.restarting = true;
    const result = await this.interop.installUpdate();
    if (typeof result !== 'boolean') {
      this.error = this.$t('update_popup.install_failed.message', {
        message: result
      }).toString();
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

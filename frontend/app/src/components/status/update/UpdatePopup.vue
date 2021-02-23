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
        <span v-if="!downloadReady">
          {{ $t('update_popup.messages') }}
        </span>
        <span v-else>{{ $t('update_popup.downloaded') }}</span>
      </v-col>
    </v-row>

    <template #action="{ attrs }">
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

  async update() {
    this.popup = false;
    const downloaded = await this.interop.downloadUpdate();
    if (downloaded) {
      this.downloadReady = true;
      this.popup = true;
    }
  }

  async install() {
    this.downloadReady = false;
    this.popup = false;
    await this.interop.installUpdate();
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

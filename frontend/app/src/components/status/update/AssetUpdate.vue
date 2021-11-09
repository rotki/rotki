<template>
  <fragment>
    <card v-if="!auto" class="mt-8">
      <template #title>{{ $t('asset_update.manual.title') }}</template>
      <template #subtitle>{{ $t('asset_update.manual.subtitle') }}</template>
      <div v-if="skipped" class="text-body-1">
        {{ $t('asset_update.manual.skipped', { skipped }) }}
      </div>
      <template #buttons>
        <v-btn depressed color="primary" class="mt-2" @click="check">
          {{ $t('asset_update.manual.check') }}
        </v-btn>
      </template>
    </card>
    <v-dialog
      v-if="showUpdateDialog"
      v-model="showUpdateDialog"
      max-width="500"
      persistent
    >
      <card>
        <template #title>{{ $t('asset_update.title') }}</template>
        <i18n class="text-body-1" tag="div" path="asset_update.description">
          <template #remote>
            <span class="font-weight-medium">{{ remoteVersion }}</span>
          </template>
          <template #local>
            <span class="font-weight-medium">{{ localVersion }}</span>
          </template>
        </i18n>
        <div class="text-body-1 mt-4">
          {{ $t('asset_update.total_changes', { changes }) }}
        </div>

        <div v-if="multiple" class="font-weight-medium text-body-1 mt-4">
          {{ $t('asset_update.advanced') }}
        </div>
        <v-row v-if="multiple">
          <v-col>
            <v-checkbox
              v-model="partial"
              class="asset-update__partial"
              dense
              :label="$t('asset_update.partially_update')"
            />
          </v-col>
          <v-col cols="6">
            <v-text-field
              v-if="partial"
              v-model="upToVersion"
              outlined
              type="number"
              dense
              :min="localVersion"
              :max="remoteVersion"
              :label="$t('asset_update.up_to_version')"
              @change="onChange"
            />
          </v-col>
        </v-row>
        <template #options>
          <v-checkbox
            v-if="auto"
            v-model="skipUpdate"
            dense
            :label="$t('asset_update.skip_notification')"
          />
        </template>
        <template #buttons>
          <v-row justify="end" no-gutters>
            <v-col cols="auto">
              <v-btn text @click="skip">
                {{ $t('asset_update.buttons.skip') }}
              </v-btn>
            </v-col>
            <v-col cols="auto">
              <v-btn text color="primary" @click="updateAssets()">
                {{ $t('asset_update.buttons.update') }}
              </v-btn>
            </v-col>
          </v-row>
        </template>
      </card>
    </v-dialog>
    <conflict-dialog
      v-if="showConflictDialog"
      v-model="showConflictDialog"
      :conflicts="conflicts"
      @cancel="showConflictDialog = false"
      @resolve="updateAssets($event)"
    />
    <confirm-dialog
      v-if="done"
      single-action
      display
      :title="$t('asset_update.success.title')"
      :primary-action="$t('asset_update.success.ok')"
      :message="
        $t('asset_update.success.description', {
          remoteVersion
        })
      "
      @confirm="updateComplete()"
    />
  </fragment>
</template>

<script lang="ts">
import { Component, Mixins, Prop } from 'vue-property-decorator';
import { mapActions } from 'vuex';
import ConfirmDialog from '@/components/dialogs/ConfirmDialog.vue';
import Fragment from '@/components/helper/Fragment';
import ConflictDialog from '@/components/status/update/ConflictDialog.vue';
import BackendMixin from '@/mixins/backend-mixin';
import {
  AssetUpdatePayload,
  ConflictResolution
} from '@/services/assets/types';
import {
  ApplyUpdateResult,
  AssetUpdateCheckResult,
  AssetUpdateConflictResult
} from '@/store/assets/types';

const SKIP_ASSET_DB_VERSION = 'rotki_skip_asset_db_version';

@Component({
  name: 'AssetUpdate',
  components: { ConfirmDialog, Fragment, ConflictDialog },
  methods: {
    ...mapActions('assets', ['checkForUpdate', 'applyUpdates']),
    ...mapActions('session', ['logout'])
  }
})
export default class AssetUpdate extends Mixins(BackendMixin) {
  @Prop({ required: false, default: false, type: Boolean })
  auto!: Boolean;
  showUpdateDialog: boolean = false;
  showConflictDialog: boolean = false;
  skipUpdate: boolean = false;
  localVersion: number = 0;
  remoteVersion: number = 0;
  changes: number = 0;
  upToVersion: number = 0;
  partial: boolean = false;
  checkForUpdate!: () => Promise<AssetUpdateCheckResult>;
  applyUpdates!: (payload: AssetUpdatePayload) => Promise<ApplyUpdateResult>;
  logout!: () => Promise<void>;
  conflicts: AssetUpdateConflictResult[] = [];
  done: boolean = false;

  get multiple(): boolean {
    return this.remoteVersion - this.localVersion > 1;
  }

  get skipped(): number | undefined {
    const skipped = localStorage.getItem(SKIP_ASSET_DB_VERSION);
    return skipped ? parseInt(skipped) : undefined;
  }

  set skipped(version: number | undefined) {
    if (version === undefined) {
      localStorage.removeItem(SKIP_ASSET_DB_VERSION);
    } else {
      localStorage.setItem(SKIP_ASSET_DB_VERSION, version.toString());
    }
  }

  async mounted() {
    if (this.$route.query.skip_update) {
      return;
    }
    if (this.auto) {
      await this.check();
    }
  }

  async check() {
    const checkResult = await this.checkForUpdate();
    const skipped = this.skipped;
    const versions = checkResult.versions;
    if (this.auto && skipped && skipped === versions?.remote) {
      return;
    }
    this.showUpdateDialog = checkResult.updateAvailable;
    if (versions) {
      this.localVersion = versions.local;
      this.remoteVersion = versions.remote;
      this.changes = versions.newChanges;
      this.upToVersion = versions.remote;
    }
  }

  skip() {
    this.showUpdateDialog = false;
    this.showConflictDialog = false;
    if (this.skipUpdate) {
      this.skipped = this.remoteVersion;
    }
  }

  onChange(value: string) {
    const number = parseInt(value);
    if (isNaN(number)) {
      this.upToVersion = this.localVersion + 1;
    } else {
      if (number < this.localVersion) {
        this.upToVersion = this.localVersion + 1;
      } else if (number > this.remoteVersion) {
        this.upToVersion = this.remoteVersion;
      } else {
        this.upToVersion = number;
      }
    }
  }

  async updateAssets(resolution?: ConflictResolution) {
    this.showUpdateDialog = false;
    this.showConflictDialog = false;
    const version = this.multiple ? this.upToVersion : this.remoteVersion;
    const updateResult = await this.applyUpdates({ version, resolution });
    if (updateResult.done) {
      this.skipped = undefined;
      this.done = true;
    } else if (updateResult.conflicts) {
      this.conflicts = updateResult.conflicts;
      this.showConflictDialog = true;
    }
  }

  async updateComplete() {
    await this.logout();
    this.$store.commit('setConnected', false);
    if (this.$interop.isPackaged) {
      await this.restartBackend();
    }
    await this.$store.dispatch('connect');
  }
}
</script>

<style scoped lang="scss">
.asset-update {
  &__partial {
    margin-top: 6px !important;
    height: 60px;
  }
}
</style>

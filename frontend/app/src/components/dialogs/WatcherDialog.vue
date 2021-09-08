<template>
  <v-dialog
    :value="display"
    persistent
    max-width="650"
    class="watcher-dialog"
    @keydown.esc.stop="cancel()"
  >
    <v-card>
      <v-card-title class="text-h5 watcher-dialog__title">
        {{ title }}
      </v-card-title>
      <v-card-text>
        <v-row align="center" class="mx-0 watcher-dialog__body">
          <v-row>
            <v-col cols="12">
              {{ message }}
            </v-col>
          </v-row>
          <v-row v-if="preselectWatcherType === ''">
            <v-col cols="12">
              <v-select
                v-model="watcherType"
                :items="watcherTypes"
                dense
                outlined
                :label="$t('watcher_dialog.labels.type')"
                required
              />
            </v-col>
          </v-row>
          <v-row v-if="loadedWatchers.length > 0">
            <v-col cols="5">
              <v-divider />
            </v-col>
            <v-col
              cols="2"
              class="pa-0 text-center"
              v-text="$t('watcher_dialog.edit')"
            />
            <v-col cols="5">
              <v-divider />
            </v-col>
          </v-row>
          <v-row v-for="(watcher, key) in loadedWatchers" :key="key">
            <v-col cols="6">
              <v-select
                :value="loadedWatchers[key].args.op"
                :items="watcherOperations[watcherType]"
                :filled="!existingWatchersEdit[watcher.identifier]"
                :readonly="!existingWatchersEdit[watcher.identifier]"
                hide-details
                outlined
                dense
                :label="$t('watcher_dialog.labels.operation')"
                required
                @input="loadedWatchers[key].args.op = $event"
              />
            </v-col>
            <v-col cols="4">
              <v-text-field
                :value="loadedWatchers[key].args.ratio"
                :label="watcherValueLabel"
                :filled="!existingWatchersEdit[watcher.identifier]"
                :readonly="!existingWatchersEdit[watcher.identifier]"
                hide-details
                outlined
                dense
                suffix="%"
                @input="loadedWatchers[key].args.ratio = $event"
              />
            </v-col>
            <v-col cols="2" class="d-flex align-center justify-space-between">
              <v-btn small icon @click="editWatcher(loadedWatchers[key])">
                <v-icon
                  small
                  v-text="existingWatchersIcon(watcher.identifier)"
                />
              </v-btn>
              <v-btn small icon @click="deleteWatcher(watcher.identifier)">
                <v-icon small> mdi-delete </v-icon>
              </v-btn>
            </v-col>
          </v-row>
          <v-row>
            <v-col cols="5">
              <v-divider />
            </v-col>
            <v-col
              cols="2"
              class="pa-0 text-center justify-center"
              v-text="$t('watcher_dialog.add_watcher')"
            />
            <v-col cols="5">
              <v-divider />
            </v-col>
          </v-row>
          <v-row>
            <v-col cols="6">
              <v-select
                v-model="watcherOperation"
                :items="watcherOperations[watcherType]"
                dense
                outlined
                hide-details
                :disabled="!watcherType"
                :label="$t('watcher_dialog.labels.operation')"
                required
              />
            </v-col>
            <v-col cols="4">
              <v-text-field
                v-model="watcherValue"
                :label="watcherValueLabel"
                hide-details
                dense
                outlined
                suffix="%"
              />
            </v-col>
            <v-col cols="2" class="d-flex align-center justify-center">
              <v-btn
                small
                icon
                class="mt-1"
                :disabled="watcherOperation === null || watcherValue === null"
                @click="addWatcher()"
              >
                <v-icon> mdi-plus </v-icon>
              </v-btn>
            </v-col>
          </v-row>
        </v-row>
      </v-card-text>

      <v-card-actions>
        <v-row class="d-flex flex-grow-1 mx-3 text-caption">
          <v-col cols="12">
            <div
              :class="`watcher-dialog__body__messages watcher-dialog__body__messages--${validationStatus} py-1 px-3`"
            >
              {{ validationMessage }}
            </div>
          </v-col>
        </v-row>
        <v-btn
          depressed
          color="primary"
          class="watcher-dialog__buttons__close"
          @click="cancel()"
          v-text="$t('watcher_dialog.close')"
        />
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script lang="ts">
import cloneDeep from 'lodash/cloneDeep';
import { Component, Emit, Prop, Vue, Watch } from 'vue-property-decorator';
import { mapActions } from 'vuex';
import {
  WatcherOpTypes,
  Watcher,
  WatcherType,
  WatcherTypes
} from '@/services/session/types';

@Component({
  methods: {
    ...mapActions('session', ['addWatchers', 'deleteWatchers', 'editWatchers'])
  }
})
export default class WatcherDialog extends Vue {
  @Prop({ required: true })
  title!: string;
  @Prop({ required: true })
  message!: string;
  @Prop({ type: Boolean, required: true })
  display!: boolean;

  @Prop({ required: false, default: 'Watcher Value' })
  watcherValueLabel!: string;
  @Prop({ required: true, default: null })
  watcherContentId!: number | null;
  @Prop({ required: false, default: '' })
  preselectWatcherType!: WatcherTypes;
  @Prop({ required: false, type: Array, default: () => [] })
  existingWatchers!: Watcher<WatcherType>[];

  watcherType: WatcherTypes | null = null;
  watcherOperation: WatcherOpTypes | null = null;
  watcherValue: string | null = null;
  validationMessage: string = '';
  validationStatus: 'success' | 'error' | '' = '';

  addWatchers!: (
    watchers: Omit<Watcher<WatcherTypes>, 'identifier'>[]
  ) => Promise<Watcher<WatcherType>[]>;
  editWatchers!: (
    watchers: Watcher<WatcherType>[]
  ) => Promise<Watcher<WatcherType>[]>;
  deleteWatchers!: (identifiers: string[]) => Promise<Watcher<WatcherType>[]>;

  loadedWatchers: Watcher<WatcherType>[] = [];
  existingWatchersEdit: {
    [identifier: string]: boolean;
  } = {};

  existingWatchersIcon(identifier: string): string {
    return this.existingWatchersEdit[identifier] ? 'mdi-check' : 'mdi-pencil';
  }

  @Watch('display')
  onDialogToggle() {
    if (this.display) {
      this.watcherType = this.preselectWatcherType;
      this.loadedWatchers = cloneDeep(this.existingWatchers);
      this.loadedWatchers.forEach(watcher => {
        this.existingWatchersEdit[watcher.identifier] = false;
      });
    } else {
      this.watcherType = null;
      this.loadedWatchers = [];
      this.existingWatchersEdit = {};
    }
  }

  watcherTypes = [
    {
      text: this.$t(
        'watcher_dialog.types.make_collateralization_ratio'
      ).toString(),
      type: 'makervault_collateralization_ratio',
      value: 'makervault_collateralization_ratio'
    }
  ];

  watcherOperations = {
    makervault_collateralization_ratio: [
      {
        op: 'gt',
        value: 'gt',
        text: this.$t('watcher_dialog.ratio.gt').toString()
      },
      {
        op: 'ge',
        value: 'ge',
        text: this.$t('watcher_dialog.ratio.ge').toString()
      },
      {
        op: 'lt',
        value: 'lt',
        text: this.$t('watcher_dialog.ratio.lt').toString()
      },
      {
        op: 'le',
        value: 'le',
        text: this.$t('watcher_dialog.ratio.le').toString()
      }
    ]
  };

  changeEditMode(identifier: string) {
    this.existingWatchersEdit = {
      ...this.existingWatchersEdit,
      [identifier]: !this.existingWatchersEdit[identifier]
    };
  }

  async deleteWatcher(identifier: string) {
    try {
      const updatedWatchers = await this.deleteWatchers([identifier]);
      this.validateSettingChange(
        'success',
        this.$t('watcher_dialog.delete_success').toString()
      );
      this.clear();
      this.updateLoadedWatchers(updatedWatchers);
    } catch (e: any) {
      this.validateSettingChange(
        'error',
        this.$t('watcher_dialog.delete_error', {
          message: e.message
        }).toString()
      );
    }
  }

  private updateLoadedWatchers(updatedWatchers: Watcher<WatcherType>[]) {
    this.loadedWatchers = cloneDeep(
      updatedWatchers.filter(
        watcher => this.watcherContentId?.toString() === watcher.args.vault_id
      )
    );
  }

  private clear() {
    this.watcherValue = null;
    this.watcherOperation = null;
  }

  async editWatcher(watcher: Watcher<WatcherType>) {
    if (!this.existingWatchersEdit[watcher.identifier]) {
      // If we're not in edit mode, just go into edit mode
      this.changeEditMode(watcher.identifier);
    } else {
      // If we're in edit mode, check to see if the values have changed before
      // sending an API call
      const existingWatcherArgs = this.existingWatchers.find(
        existingWatcher => existingWatcher.identifier === watcher.identifier
      )!.args;
      const modifiedWatcherArgs = watcher.args;

      if (
        existingWatcherArgs.op !== modifiedWatcherArgs.op ||
        existingWatcherArgs.ratio !== modifiedWatcherArgs.ratio
      ) {
        try {
          const updatedWatchers = await this.editWatchers([watcher]);
          this.validateSettingChange(
            'success',
            this.$t('watcher_dialog.edit_success').toString()
          );
          this.changeEditMode(watcher.identifier);
          this.updateLoadedWatchers(updatedWatchers);
        } catch (e: any) {
          this.validateSettingChange(
            'error',
            this.$t('watcher_dialog.edit_error', {
              message: e.message
            }).toString()
          );
        }
      } else {
        this.changeEditMode(watcher.identifier);
      }
    }
  }

  async addWatcher() {
    if (
      !(
        this.watcherType &&
        this.watcherValue &&
        this.watcherOperation &&
        this.watcherContentId
      )
    ) {
      return;
    }

    const watcherData: Omit<Watcher<WatcherType>, 'identifier'> = {
      type: this.watcherType,
      args: {
        ratio: this.watcherValue,
        op: this.watcherOperation,
        vault_id: this.watcherContentId.toString()
      }
    };

    try {
      const updatedWatchers = await this.addWatchers([watcherData]);
      this.validateSettingChange(
        'success',
        this.$t('watcher_dialog.add_success').toString()
      );
      this.clear();
      this.updateLoadedWatchers(updatedWatchers);
    } catch (e: any) {
      this.validateSettingChange(
        'error',
        this.$t('watcher_dialog.add_error', { message: e.message }).toString()
      );
    }
  }

  validateSettingChange(
    targetState: string,
    message: string = '',
    timeOut: number = 5500
  ) {
    if (targetState === 'success' || targetState === 'error') {
      setTimeout(() => {
        this.validationMessage = message;
        this.validationStatus = targetState;
      }, 200);
      setTimeout(() => {
        this.validationMessage = '';
        this.validationStatus = '';
      }, timeOut);
    }
  }

  @Emit()
  cancel() {
    for (const index in this.existingWatchersEdit) {
      // Reset edit mode on all fields
      this.existingWatchersEdit[index] = false;
      this.clear();
      // Reset unsaved changes to the current saved state
      this.loadedWatchers = cloneDeep(this.existingWatchers);
    }
  }
}
</script>

<style scoped lang="scss">
.watcher-dialog {
  &__body {
    padding: 0 16px;

    &__messages {
      min-height: 2.5em;
      border-radius: 8px;

      &--success {
        background-color: var(--v-success-lighten4);
        color: var(--v-success-darken2);
      }

      &--error {
        background-color: var(--v-error-lighten4);
        color: var(--v-error-darken2);
      }
    }

    ::v-deep {
      .v-text-field {
        &--filled {
          .v-text-field {
            &__suffix {
              margin-top: 0;
            }
          }
        }
      }
    }
  }
}
</style>

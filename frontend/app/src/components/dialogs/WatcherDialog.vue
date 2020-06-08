<template>
  <v-dialog
    :value="display"
    persistent
    max-width="650"
    class="watcher-dialog"
    @keydown.esc.stop="cancel()"
  >
    <v-card>
      <v-card-title class="headline watcher-dialog__title">
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
                label="Watcher Type"
                required
              >
              </v-select>
            </v-col>
          </v-row>
          <v-row v-if="loadedWatchers.length > 0">
            <v-col cols="5">
              <v-divider></v-divider>
            </v-col>
            <v-col cols="2" class="pa-0 text-center">
              Edit watchers
            </v-col>
            <v-col cols="5">
              <v-divider></v-divider>
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
                label="Operation"
                required
                @input="loadedWatchers[key].args.op = $event"
              >
              </v-select>
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
              ></v-text-field>
            </v-col>
            <v-col cols="2" class="d-flex align-center justify-space-between">
              <v-btn small icon @click="editWatcher(loadedWatchers[key])">
                <v-icon small>
                  fa
                  {{
                    existingWatchersEdit[watcher.identifier]
                      ? 'fa-check'
                      : 'fa-pencil'
                  }}
                </v-icon>
              </v-btn>
              <v-btn small icon @click="deleteWatcher(watcher.identifier)">
                <v-icon small>
                  fa fa-trash
                </v-icon>
              </v-btn>
            </v-col>
          </v-row>
          <v-row>
            <v-col cols="5">
              <v-divider></v-divider>
            </v-col>
            <v-col cols="2" class="pa-0 text-center justify-center">
              Add watcher
            </v-col>
            <v-col cols="5">
              <v-divider></v-divider>
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
                label="Operation"
                required
              >
              </v-select>
            </v-col>
            <v-col cols="4">
              <v-text-field
                v-model="watcherValue"
                :label="watcherValueLabel"
                hide-details
                dense
                outlined
                suffix="%"
              ></v-text-field>
            </v-col>
            <v-col cols="2" class="d-flex align-center justify-center">
              <v-btn
                small
                icon
                class="mt-1"
                :disabled="watcherOperation === null || watcherValue === null"
                @click="addWatcher()"
              >
                <v-icon>
                  fa fa-plus
                </v-icon>
              </v-btn>
            </v-col>
          </v-row>
        </v-row>
      </v-card-text>

      <v-card-actions>
        <v-spacer></v-spacer>
        <v-btn
          depressed
          color="primary"
          class="watcher-dialog__buttons__close"
          @click="cancel()"
        >
          Close
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script lang="ts">
import { Component, Emit, Prop, Vue, Watch } from 'vue-property-decorator';
import MessageDialog from '@/components/dialogs/MessageDialog.vue';
import { Watcher, WatcherArgs } from '@/services/types-api';
import { WatcherType } from '@/services/types-common';
import { Message } from '@/store/store';

@Component({
  components: { MessageDialog }
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
  watcherContentId!: string | number | null;
  @Prop({ required: false, default: '' })
  preselectWatcherType!: string;
  @Prop({ required: false, type: Array, default: () => [] })
  existingWatchers!: Watcher[];

  watcherType: string | null = null;
  watcherOperation: string | null = null;
  watcherValue: string | null = null;

  loadedWatchers: Watcher[] = [];
  existingWatchersEdit: {
    [identifier: string]: boolean;
  } = {};

  // mounted() {
  //   this.watcherType = this.preselectWatcherType;
  //   this.loadedWatchers = JSON.parse(JSON.stringify(this.existingWatchers)); // make a non-reactive copy

  //   this.loadedWatchers.forEach(watcher => {
  //     this.existingWatchersEdit[watcher.identifier] = false;
  //   });
  // }

  @Watch('display')
  onDialogToggle() {
    if (this.display) {
      this.watcherType = this.preselectWatcherType;
      this.loadedWatchers = JSON.parse(JSON.stringify(this.existingWatchers)); // make a non-reactive copy
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
      text: 'Collateralization Ratio Watcher (Maker)',
      type: 'makervault_collateralization_ratio',
      value: 'makervault_collateralization_ratio'
    }
  ];

  watcherOperations = {
    makervault_collateralization_ratio: [
      { op: 'gt', value: 'gt', text: 'greater than' },
      { op: 'ge', value: 'ge', text: 'greater than or equal to' },
      { op: 'lt', value: 'lt', text: 'less than' },
      { op: 'le', value: 'le', text: 'less than or equal to' }
    ]
  };

  changeEditMode(identifier: string) {
    this.existingWatchersEdit = {
      ...this.existingWatchersEdit,
      [identifier]: !this.existingWatchersEdit[identifier]
    };
  }

  deleteWatcher(watcher: string) {
    let watcherPayload: string[] = [];
    watcherPayload.push(watcher);

    const { commit } = this.$store;
    this.$api
      .deleteWatcher(watcherPayload)
      .then(updatedWatchers => {
        commit('balances/watchers', updatedWatchers);
        commit('setMessage', {
          title: 'Watcher Success',
          description: 'Successfully deleted the watcher.',
          success: true
        } as Message);
        this.watcherValue = null;
        this.watcherOperation = null;
        this.loadedWatchers = JSON.parse(JSON.stringify(updatedWatchers));
      })
      .catch((reason: Error) => {
        commit('setMessage', {
          title: 'Watcher Error',
          description: reason.message || 'Error deleting the watcher',
          success: false
        } as Message);
      });
  }

  editWatcher(watcher: Watcher) {
    if (this.existingWatchersEdit[watcher.identifier] === false) {
      // If we're not in edit mode, just go into edit mode
      this.changeEditMode(watcher.identifier);
    } else {
      // If we're in edit mode, check to see if the values have changed before
      // sending an API call
      const existingWatcherArgs = this.existingWatchers.find(
        existingWatcher => existingWatcher.identifier === watcher.identifier
      )!.args as WatcherArgs['makervault_collateralization_ratio'];
      const modifiedWatcherArgs = watcher.args as WatcherArgs['makervault_collateralization_ratio'];

      if (
        existingWatcherArgs.op !== modifiedWatcherArgs.op ||
        existingWatcherArgs.ratio !== modifiedWatcherArgs.ratio
      ) {
        let watcherPayload: Watcher[] = [];
        watcherPayload.push(watcher);

        const { commit } = this.$store;
        this.$api
          .editWatcher(watcherPayload)
          .then(updatedWatchers => {
            commit('balances/watchers', updatedWatchers);
            commit('setMessage', {
              title: 'Watcher Success',
              description: 'Successfully edited the watcher.',
              success: true
            } as Message);
            this.changeEditMode(watcher.identifier);
            this.loadedWatchers = JSON.parse(JSON.stringify(updatedWatchers));
          })
          .catch((reason: Error) => {
            commit('setMessage', {
              title: 'Watcher Error',
              description: reason.message || 'Error editing the watcher',
              success: false
            } as Message);
          });
      } else {
        this.changeEditMode(watcher.identifier);
      }
    }
  }

  addWatcher() {
    let watcherPayload: Omit<Watcher, 'identifier'>[] = [];

    if (
      this.watcherType &&
      this.watcherValue &&
      this.watcherOperation &&
      this.watcherContentId
    ) {
      const { commit } = this.$store;
      const watcherData: Omit<Watcher, 'identifier'> = {
        type: this.watcherType as WatcherType,
        args: {
          ratio: this.watcherValue,
          op: this.watcherOperation,
          vault_id: this.watcherContentId.toString()
        }
      };
      watcherPayload.push(watcherData);

      this.$api
        .addWatcher(watcherPayload)
        .then(updatedWatchers => {
          commit('balances/watchers', updatedWatchers);
          commit('setMessage', {
            title: 'Watcher Success',
            description: 'Successfully added the watcher.',
            success: true
          } as Message);
          this.watcherValue = null;
          this.watcherOperation = null;
          this.loadedWatchers = JSON.parse(JSON.stringify(updatedWatchers));
        })
        .catch((reason: Error) => {
          commit('setMessage', {
            title: 'Watcher Error',
            description: reason.message || 'Error adding the watcher',
            success: false
          } as Message);
        });
    }
  }

  @Emit()
  cancel() {
    for (const index in this.existingWatchersEdit) {
      // Reset edit mode on all fields
      this.existingWatchersEdit[index] = false;

      // Reset unsaved changes to the current saved state
      this.loadedWatchers = JSON.parse(JSON.stringify(this.existingWatchers));
    }
  }
}
</script>

<style scoped lang="scss">
.watcher-dialog {
  &__body {
    padding: 0 16px;

    ::v-deep .v-text-field--filled .v-text-field__suffix {
      margin-top: 0px;
    }
  }
}
</style>

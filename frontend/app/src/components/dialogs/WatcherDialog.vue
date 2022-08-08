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
        <v-row align="center" class="watcher-dialog__body">
          <v-col cols="12">
            {{ message }}
          </v-col>
          <v-col v-if="preselectWatcherType === ''" cols="12">
            <v-select
              v-model="watcherType"
              :items="watcherTypes"
              :label="$t('watcher_dialog.labels.type')"
              dense
              outlined
              required
            />
          </v-col>
          <v-col v-if="loadedWatchers.length > 0" cols="12">
            <v-row>
              <v-col cols="5">
                <v-divider />
              </v-col>
              <v-col
                class="pa-0 text-center"
                cols="2"
                v-text="$t('watcher_dialog.edit')"
              />
              <v-col cols="5">
                <v-divider />
              </v-col>
            </v-row>
            <v-row
              v-for="(watcher, key) in loadedWatchers"
              :key="key"
              align="center"
            >
              <v-col cols="6">
                <v-select
                  :filled="!existingWatchersEdit[watcher.identifier]"
                  :items="watcherOperations[watcherType]"
                  :label="$t('watcher_dialog.labels.operation')"
                  :readonly="!existingWatchersEdit[watcher.identifier]"
                  :value="loadedWatchers[key].args.op"
                  dense
                  hide-details
                  outlined
                  required
                  @input="loadedWatchers[key].args.op = $event"
                />
              </v-col>
              <v-col cols="4">
                <v-text-field
                  :filled="!existingWatchersEdit[watcher.identifier]"
                  :label="watcherValueLabel"
                  :readonly="!existingWatchersEdit[watcher.identifier]"
                  :value="loadedWatchers[key].args.ratio"
                  dense
                  hide-details
                  outlined
                  suffix="%"
                  @input="loadedWatchers[key].args.ratio = $event"
                />
              </v-col>
              <v-col class="d-flex align-center justify-space-between" cols="2">
                <v-btn icon @click="editWatcher(loadedWatchers[key])">
                  <v-icon
                    small
                    v-text="existingWatchersIcon(watcher.identifier)"
                  />
                </v-btn>
                <v-btn icon @click="deleteWatcher(watcher.identifier)">
                  <v-icon small> mdi-delete </v-icon>
                </v-btn>
              </v-col>
            </v-row>
          </v-col>
          <v-col cols="12">
            <v-row>
              <v-col cols="5">
                <v-divider />
              </v-col>
              <v-col
                class="pa-0 text-center justify-center"
                cols="2"
                v-text="$t('watcher_dialog.add_watcher')"
              />
              <v-col cols="5">
                <v-divider />
              </v-col>
            </v-row>
            <v-row align="center">
              <v-col cols="6">
                <v-select
                  v-model="watcherOperation"
                  :disabled="!watcherType"
                  :items="watcherOperations[watcherType]"
                  :label="$t('watcher_dialog.labels.operation')"
                  dense
                  hide-details
                  outlined
                  required
                />
              </v-col>
              <v-col cols="5">
                <v-text-field
                  v-model="watcherValue"
                  :label="watcherValueLabel"
                  dense
                  hide-details
                  outlined
                  suffix="%"
                />
              </v-col>
              <v-col class="d-flex align-center justify-center" cols="1">
                <v-btn
                  :disabled="watcherOperation === null || watcherValue === null"
                  icon
                  @click="addWatcher()"
                >
                  <v-icon> mdi-plus </v-icon>
                </v-btn>
              </v-col>
            </v-row>
          </v-col>
        </v-row>
      </v-card-text>

      <v-card-actions class="watcher-dialog__actions">
        <div
          :class="`text-caption flex-1 watcher-dialog__actions__messages watcher-dialog__actions__messages--${validationStatus} py-1 px-3 mr-4`"
        >
          {{ validationMessage }}
        </div>
        <v-btn
          depressed
          color="primary"
          class="watcher-dialog__buttons__close"
          @click="cancel()"
          v-text="$t('common.actions.close')"
        />
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script lang="ts">
import {
  computed,
  defineComponent,
  PropType,
  ref,
  Ref,
  toRefs,
  watch
} from '@vue/composition-api';
import { get, set } from '@vueuse/core';
import { storeToRefs } from 'pinia';
import i18n from '@/i18n';
import {
  WatcherOpTypes,
  Watcher,
  WatcherType,
  WatcherTypes
} from '@/services/session/types';
import { useWatchersStore } from '@/store/session/watchers';

export default defineComponent({
  name: 'WatcherDialog',
  props: {
    title: { required: true, type: String },
    message: { required: true, type: String },
    display: { required: true, type: Boolean },
    watcherValueLabel: {
      required: false,
      type: String,
      default: 'Watcher Value'
    },
    watcherContentId: {
      required: false,
      type: String,
      default: null
    },
    preselectWatcherType: {
      required: false,
      type: String as PropType<WatcherTypes>,
      default: ''
    },
    existingWatchers: {
      required: false,
      type: Array as PropType<Watcher<WatcherType>[]>,
      default: () => []
    }
  },
  emits: ['cancel'],
  setup(props, { emit }) {
    const {
      display,
      preselectWatcherType,
      existingWatchers,
      watcherContentId
    } = toRefs(props);
    const watcherType: Ref<WatcherTypes | null> = ref(null);
    const watcherOperation: Ref<WatcherOpTypes | null> = ref(null);
    const watcherValue: Ref<string | null> = ref(null);
    const validationMessage: Ref<string> = ref('');
    const validationStatus: Ref<'success' | 'error' | ''> = ref('');
    const existingWatchersEdit: Ref<Record<string, boolean>> = ref({});

    let store = useWatchersStore();
    const { watchers } = storeToRefs(store);
    const { addWatchers, editWatchers, deleteWatchers } = store;

    const loadedWatchers = computed(() => {
      const id = get(watcherContentId)?.toString();
      return get(watchers).filter(watcher => watcher.args.vault_id === id);
    });

    const watcherTypes = computed(() => [
      {
        text: i18n
          .t('watcher_dialog.types.make_collateralization_ratio')
          .toString(),
        type: 'makervault_collateralization_ratio',
        value: 'makervault_collateralization_ratio'
      }
    ]);

    const watcherOperations = computed(() => ({
      makervault_collateralization_ratio: [
        {
          op: 'gt',
          value: 'gt',
          text: i18n.t('watcher_dialog.ratio.gt').toString()
        },
        {
          op: 'ge',
          value: 'ge',
          text: i18n.t('watcher_dialog.ratio.ge').toString()
        },
        {
          op: 'lt',
          value: 'lt',
          text: i18n.t('watcher_dialog.ratio.lt').toString()
        },
        {
          op: 'le',
          value: 'le',
          text: i18n.t('watcher_dialog.ratio.le').toString()
        }
      ]
    }));

    const existingWatchersIcon = (identifier: string): string => {
      const edit = get(existingWatchersEdit);
      return edit[identifier] ? 'mdi-check' : 'mdi-pencil';
    };

    const validateSettingChange = (
      targetState: string,
      message: string = '',
      timeOut: number = 5500
    ) => {
      if (targetState === 'success' || targetState === 'error') {
        setTimeout(() => {
          set(validationMessage, message);
          set(validationStatus, targetState);
        }, 200);
        setTimeout(() => {
          set(validationMessage, '');
          set(validationStatus, '');
        }, timeOut);
      }
    };

    const changeEditMode = (identifier: string) => {
      const edit = get(existingWatchersEdit);
      set(existingWatchersEdit, {
        ...edit,
        [identifier]: !edit[identifier]
      });
    };

    const addWatcher = async () => {
      const type = get(watcherType);
      const value = get(watcherValue);
      const operation = get(watcherOperation);
      const contentId = get(watcherContentId);
      if (!(type && value && operation && contentId)) {
        return;
      }

      const watcherData: Omit<Watcher<WatcherType>, 'identifier'> = {
        type: type,
        args: {
          ratio: value,
          op: operation,
          vault_id: contentId.toString()
        }
      };

      try {
        await addWatchers([watcherData]);
        validateSettingChange(
          'success',
          i18n.t('watcher_dialog.add_success').toString()
        );
        clear();
      } catch (e: any) {
        validateSettingChange(
          'error',
          i18n.t('watcher_dialog.add_error', { message: e.message }).toString()
        );
      }
    };

    const editWatcher = async (watcher: Watcher<WatcherType>) => {
      const edit = get(existingWatchersEdit);
      if (!edit[watcher.identifier]) {
        // If we're not in edit mode, just go into edit mode
        changeEditMode(watcher.identifier);
      } else {
        // If we're in edit mode, check to see if the values have changed before
        // sending an API call
        const existingWatcherArgs = get(existingWatchers).find(
          existingWatcher => existingWatcher.identifier === watcher.identifier
        )!.args;
        const modifiedWatcherArgs = watcher.args;

        if (
          existingWatcherArgs.op !== modifiedWatcherArgs.op ||
          existingWatcherArgs.ratio !== modifiedWatcherArgs.ratio
        ) {
          try {
            await editWatchers([watcher]);
            validateSettingChange(
              'success',
              i18n.t('watcher_dialog.edit_success').toString()
            );
            changeEditMode(watcher.identifier);
          } catch (e: any) {
            validateSettingChange(
              'error',
              i18n
                .t('watcher_dialog.edit_error', {
                  message: e.message
                })
                .toString()
            );
          }
        } else {
          changeEditMode(watcher.identifier);
        }
      }
    };

    const deleteWatcher = async (identifier: string) => {
      try {
        await deleteWatchers([identifier]);
        validateSettingChange(
          'success',
          i18n.t('watcher_dialog.delete_success').toString()
        );
        clear();
      } catch (e: any) {
        validateSettingChange(
          'error',
          i18n
            .t('watcher_dialog.delete_error', {
              message: e.message
            })
            .toString()
        );
      }
    };

    const clear = () => {
      set(watcherValue, null);
      set(watcherOperation, null);
    };

    watch(display, display => {
      if (display) {
        set(watcherType, get(preselectWatcherType));

        const edit = { ...get(existingWatchersEdit) };
        get(loadedWatchers).forEach(watcher => {
          edit[watcher.identifier] = false;
        });
        set(existingWatchersEdit, edit);
      } else {
        set(watcherType, null);
        set(existingWatchersEdit, {});
      }
    });

    const cancel = () => {
      emit('cancel');
      const edit = { ...get(existingWatchersEdit) };
      for (const index in edit) {
        // Reset edit mode on all fields
        edit[index] = false;
      }
      // Reset unsaved changes to the current saved state
      set(existingWatchersEdit, edit);
      clear();
    };

    return {
      loadedWatchers,
      watcherValue,
      watcherType,
      watcherTypes,
      watcherOperation,
      watcherOperations,
      validationMessage,
      validationStatus,
      existingWatchersEdit,
      addWatcher,
      editWatcher,
      deleteWatcher,
      existingWatchersIcon,
      clear,
      cancel
    };
  }
});
</script>

<style lang="scss" scoped>
.watcher-dialog {
  &__body {
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

  &__actions {
    padding: 1rem 1.5rem !important;
    justify-content: space-between;

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
  }
}
</style>

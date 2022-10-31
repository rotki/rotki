<template>
  <v-dialog
    :value="display"
    persistent
    max-width="650"
    class="watcher-dialog"
    @keydown.esc.stop="cancel()"
  >
    <card>
      <template #title> {{ title }} </template>
      <v-row align="center" class="watcher-dialog__body">
        <v-col cols="12">
          {{ message }}
        </v-col>
        <v-col v-if="!preselectWatcherType" cols="12">
          <v-select
            v-model="watcherType"
            :items="watcherTypes"
            :label="tc('watcher_dialog.labels.type')"
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
            <v-col class="pa-0 text-center" cols="2">
              {{ tc('watcher_dialog.edit') }}
            </v-col>
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
                :items="operations"
                :label="tc('watcher_dialog.labels.operation')"
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
                <v-icon small>
                  {{ existingWatchersIcon(watcher.identifier) }}
                </v-icon>
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
            <v-col class="pa-0 text-center justify-center" cols="2">
              {{ tc('watcher_dialog.add_watcher') }}
            </v-col>
            <v-col cols="5">
              <v-divider />
            </v-col>
          </v-row>
          <v-row align="center">
            <v-col cols="6">
              <v-select
                v-model="watcherOperation"
                :disabled="!watcherType"
                :items="operations"
                :label="tc('watcher_dialog.labels.operation')"
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
      <template #buttons>
        <div class="watcher-dialog__actions">
          <div
            :class="`text-caption flex-1 watcher-dialog__actions__messages watcher-dialog__actions__messages--${validationStatus} py-2 px-4 mb-4`"
          >
            {{ validationMessage }}
          </div>
          <v-btn
            depressed
            color="primary"
            class="watcher-dialog__buttons__close"
            @click="cancel()"
          >
            {{ tc('common.actions.close') }}
          </v-btn>
        </div>
      </template>
    </card>
  </v-dialog>
</template>

<script setup lang="ts">
import { PropType, Ref } from 'vue';
import {
  Watcher,
  WatcherOpTypes,
  WatcherType,
  WatcherTypes
} from '@/services/session/types';
import { useWatchersStore } from '@/store/session/watchers';

const props = defineProps({
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
    type: [String, Number],
    default: null
  },
  preselectWatcherType: {
    required: false,
    type: String as PropType<WatcherTypes>,
    default: null
  },
  existingWatchers: {
    required: false,
    type: Array as PropType<Watcher<WatcherType>[]>,
    default: () => []
  }
});

const emit = defineEmits(['cancel']);

const { display, preselectWatcherType, existingWatchers, watcherContentId } =
  toRefs(props);
const watcherType: Ref<WatcherTypes | null> = ref(null);
const watcherOperation: Ref<WatcherOpTypes | null> = ref(null);
const watcherValue: Ref<string | null> = ref(null);
const validationMessage: Ref<string> = ref('');
const validationStatus: Ref<'success' | 'error' | ''> = ref('');
const existingWatchersEdit: Ref<Record<string, boolean>> = ref({});

const { tc } = useI18n();

let store = useWatchersStore();
const { watchers } = storeToRefs(store);
const { addWatchers, editWatchers, deleteWatchers } = store;

const loadedWatchers = computed(() => {
  const id = get(watcherContentId)?.toString();
  return get(watchers).filter(watcher => watcher.args.vault_id === id);
});

const watcherTypes = computed(() => [
  {
    text: tc('watcher_dialog.types.make_collateralization_ratio'),
    type: 'makervault_collateralization_ratio',
    value: 'makervault_collateralization_ratio'
  }
]);

const watcherOperations = computed(() => ({
  makervault_collateralization_ratio: [
    {
      op: 'gt',
      value: 'gt',
      text: tc('watcher_dialog.ratio.gt')
    },
    {
      op: 'ge',
      value: 'ge',
      text: tc('watcher_dialog.ratio.ge')
    },
    {
      op: 'lt',
      value: 'lt',
      text: tc('watcher_dialog.ratio.lt')
    },
    {
      op: 'le',
      value: 'le',
      text: tc('watcher_dialog.ratio.le')
    }
  ]
}));

const operations = computed(() => {
  let operations = get(watcherOperations);
  const type = get(watcherType);
  if (!type) {
    return [];
  }
  return operations[type] ?? [];
});

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
    validateSettingChange('success', tc('watcher_dialog.add_success'));
    clear();
  } catch (e: any) {
    validateSettingChange(
      'error',
      tc('watcher_dialog.add_error', 0, { message: e.message })
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
        validateSettingChange('success', tc('watcher_dialog.edit_success'));
        changeEditMode(watcher.identifier);
      } catch (e: any) {
        validateSettingChange(
          'error',
          tc('watcher_dialog.edit_error', 0, {
            message: e.message
          })
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
    validateSettingChange('success', tc('watcher_dialog.delete_success'));
    clear();
  } catch (e: any) {
    validateSettingChange(
      'error',
      tc('watcher_dialog.delete_error', 0, {
        message: e.message
      })
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
</script>

<style lang="scss" scoped>
.watcher-dialog {
  &__body {
    :deep() {
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
    width: 100%;
    justify-content: space-between;

    &__messages {
      min-height: 2.5em;
      width: 100%;
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

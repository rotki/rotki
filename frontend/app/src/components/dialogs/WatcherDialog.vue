<script setup lang="ts">
import { type ComputedRef, type PropType, type Ref } from 'vue';
import cloneDeep from 'lodash/cloneDeep';
import {
  type Watcher,
  type WatcherOpTypes,
  WatcherType
} from '@/types/session';

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
    type: String as PropType<typeof WatcherType>,
    default: null
  },
  existingWatchers: {
    required: false,
    type: Array as PropType<Watcher[]>,
    default: () => []
  }
});

const emit = defineEmits(['cancel']);

const { display, preselectWatcherType, existingWatchers, watcherContentId } =
  toRefs(props);
const watcherType: Ref<typeof WatcherType | null> = ref(null);
const watcherOperation: Ref<WatcherOpTypes | null> = ref(null);
const watcherValue: Ref<string | null> = ref(null);
const validationMessage: Ref<string> = ref('');
const validationStatus: Ref<'success' | 'error' | ''> = ref('');
const existingWatchersEdit: Ref<Record<string, boolean>> = ref({});

const { t } = useI18n();

const store = useWatchersStore();
const { watchers } = storeToRefs(store);
const { addWatchers, editWatchers, deleteWatchers } = store;

const loadedWatchers: ComputedRef<Watcher[]> = computed(() => {
  const id = get(watcherContentId)?.toString();
  return cloneDeep(get(watchers)).filter(
    watcher => watcher.args.vaultId === id
  );
});

const watcherTypes = computed(() => [
  {
    text: t('watcher_dialog.types.make_collateralization_ratio'),
    type: WatcherType,
    value: WatcherType
  }
]);

const watcherOperations = computed(() => ({
  makervault_collateralization_ratio: [
    {
      op: 'gt',
      value: 'gt',
      text: t('watcher_dialog.ratio.gt')
    },
    {
      op: 'ge',
      value: 'ge',
      text: t('watcher_dialog.ratio.ge')
    },
    {
      op: 'lt',
      value: 'lt',
      text: t('watcher_dialog.ratio.lt')
    },
    {
      op: 'le',
      value: 'le',
      text: t('watcher_dialog.ratio.le')
    }
  ]
}));

const operations = computed(() => {
  const operations = get(watcherOperations);
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
  message = '',
  timeOut = 5500
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

  const watcherData: Omit<Watcher, 'identifier'> = {
    type,
    args: {
      ratio: value,
      op: operation,
      vaultId: contentId.toString()
    }
  };

  try {
    await addWatchers([watcherData]);
    validateSettingChange('success', t('watcher_dialog.add_success'));
    clear();
  } catch (e: any) {
    validateSettingChange(
      'error',
      t('watcher_dialog.add_error', { message: e.message })
    );
  }
};

const editWatcher = async (watcher: Watcher) => {
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
        validateSettingChange('success', t('watcher_dialog.edit_success'));
        changeEditMode(watcher.identifier);
      } catch (e: any) {
        validateSettingChange(
          'error',
          t('watcher_dialog.edit_error', {
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
    validateSettingChange('success', t('watcher_dialog.delete_success'));
    clear();
  } catch (e: any) {
    validateSettingChange(
      'error',
      t('watcher_dialog.delete_error', {
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

<template>
  <VDialog
    :value="display"
    persistent
    max-width="650"
    class="watcher-dialog"
    @keydown.esc.stop="cancel()"
  >
    <Card>
      <template #title> {{ title }} </template>
      <VRow align="center" class="watcher-dialog__body">
        <VCol cols="12">
          {{ message }}
        </VCol>
        <VCol v-if="!preselectWatcherType" cols="12">
          <VSelect
            v-model="watcherType"
            :items="watcherTypes"
            :label="t('watcher_dialog.labels.type')"
            dense
            outlined
            required
          />
        </VCol>
        <VCol v-if="loadedWatchers.length > 0" cols="12">
          <VRow>
            <VCol cols="5">
              <VDivider />
            </VCol>
            <VCol class="pa-0 text-center" cols="2">
              {{ t('watcher_dialog.edit') }}
            </VCol>
            <VCol cols="5">
              <VDivider />
            </VCol>
          </VRow>
          <VRow
            v-for="(watcher, key) in loadedWatchers"
            :key="key"
            align="center"
          >
            <VCol cols="6">
              <VSelect
                :filled="!existingWatchersEdit[watcher.identifier]"
                :items="operations"
                :label="t('watcher_dialog.labels.operation')"
                :readonly="!existingWatchersEdit[watcher.identifier]"
                :value="loadedWatchers[key].args.op"
                dense
                hide-details
                outlined
                required
                @input="loadedWatchers[key].args.op = $event"
              />
            </VCol>
            <VCol cols="4">
              <VTextField
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
            </VCol>
            <VCol class="flex items-center justify-between" cols="2">
              <VBtn icon @click="editWatcher(loadedWatchers[key])">
                <VIcon small>
                  {{ existingWatchersIcon(watcher.identifier) }}
                </VIcon>
              </VBtn>
              <VBtn icon @click="deleteWatcher(watcher.identifier)">
                <VIcon small> mdi-delete </VIcon>
              </VBtn>
            </VCol>
          </VRow>
        </VCol>
        <VCol cols="12">
          <VRow>
            <VCol cols="5">
              <VDivider />
            </VCol>
            <VCol class="pa-0 text-center justify-center" cols="2">
              {{ t('watcher_dialog.add_watcher') }}
            </VCol>
            <VCol cols="5">
              <VDivider />
            </VCol>
          </VRow>
          <VRow align="center">
            <VCol cols="6">
              <VSelect
                v-model="watcherOperation"
                :disabled="!watcherType"
                :items="operations"
                :label="t('watcher_dialog.labels.operation')"
                dense
                hide-details
                outlined
                required
              />
            </VCol>
            <VCol cols="5">
              <VTextField
                v-model="watcherValue"
                :label="watcherValueLabel"
                dense
                hide-details
                outlined
                suffix="%"
              />
            </VCol>
            <VCol class="flex items-center justify-center" cols="1">
              <VBtn
                :disabled="watcherOperation === null || watcherValue === null"
                icon
                @click="addWatcher()"
              >
                <VIcon> mdi-plus </VIcon>
              </VBtn>
            </VCol>
          </VRow>
        </VCol>
      </VRow>
      <template #buttons>
        <div class="watcher-dialog__actions">
          <div
            :class="`text-caption flex-1 watcher-dialog__actions__messages watcher-dialog__actions__messages--${validationStatus} py-2 px-4 mb-4`"
          >
            {{ validationMessage }}
          </div>
          <VBtn
            depressed
            color="primary"
            class="watcher-dialog__buttons__close"
            @click="cancel()"
          >
            {{ t('common.actions.close') }}
          </VBtn>
        </div>
      </template>
    </Card>
  </VDialog>
</template>

<style lang="scss" scoped>
.watcher-dialog {
  &__body {
    /* stylelint-disable selector-class-pattern,selector-nested-pattern */

    :deep(.v-text-field--filled) {
      /* stylelint-enable selector-class-pattern,selector-nested-pattern */

      .v-text-field {
        &__suffix {
          margin-top: 0;
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

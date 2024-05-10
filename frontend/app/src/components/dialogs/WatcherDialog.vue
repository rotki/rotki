<script setup lang="ts">
import { cloneDeep } from 'lodash-es';
import {
  type Watcher,
  type WatcherOpTypes,
  WatcherType,
} from '@/types/session';

const props = withDefaults(
  defineProps<{
    title: string;
    message: string;
    display: boolean;
    watcherValueLabel?: string;
    watcherContentId?: string | number;
    preselectWatcherType?: typeof WatcherType;
    existingWatchers?: Watcher[];
  }>(),
  {
    watcherValueLabel: 'Watcher Value',
    watcherContentId: undefined,
    preselectWatcherType: undefined,
    existingWatchers: () => [],
  },
);

const emit = defineEmits<{ (e: 'cancel'): void }>();

const { display, preselectWatcherType, existingWatchers, watcherContentId }
  = toRefs(props);
const watcherType: Ref<typeof WatcherType | null> = ref(null);
const watcherOperation: Ref<WatcherOpTypes | null> = ref(null);
const watcherValue: Ref<string | undefined> = ref();
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
    watcher => watcher.args.vaultId === id,
  );
});

const watcherTypes = computed(() => [
  {
    text: t('watcher_dialog.types.make_collateralization_ratio'),
    type: WatcherType,
    value: WatcherType,
  },
]);

const watcherOperations = computed(() => ({
  makervault_collateralization_ratio: [
    {
      op: 'gt',
      value: 'gt',
      text: t('watcher_dialog.ratio.gt'),
    },
    {
      op: 'ge',
      value: 'ge',
      text: t('watcher_dialog.ratio.ge'),
    },
    {
      op: 'lt',
      value: 'lt',
      text: t('watcher_dialog.ratio.lt'),
    },
    {
      op: 'le',
      value: 'le',
      text: t('watcher_dialog.ratio.le'),
    },
  ],
}));

const operations = computed(() => {
  const operations = get(watcherOperations);
  const type = get(watcherType);
  if (!type)
    return [];

  return operations[type] ?? [];
});

function existingWatchersIcon(identifier: string): string {
  const edit = get(existingWatchersEdit);
  return edit[identifier] ? 'check-line' : 'pencil-line';
}

function validateSettingChange(targetState: string, message = '', timeOut = 5500) {
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
}

function changeEditMode(identifier: string) {
  const edit = get(existingWatchersEdit);
  set(existingWatchersEdit, {
    ...edit,
    [identifier]: !edit[identifier],
  });
}

async function addWatcher() {
  const type = get(watcherType);
  const value = get(watcherValue);
  const operation = get(watcherOperation);
  const contentId = get(watcherContentId);
  if (!(type && value && operation && contentId))
    return;

  const watcherData: Omit<Watcher, 'identifier'> = {
    type,
    args: {
      ratio: value,
      op: operation,
      vaultId: contentId.toString(),
    },
  };

  try {
    await addWatchers([watcherData]);
    validateSettingChange('success', t('watcher_dialog.add_success'));
    clear();
  }
  catch (error: any) {
    validateSettingChange(
      'error',
      t('watcher_dialog.add_error', { message: error.message }),
    );
  }
}

async function editWatcher(watcher: Watcher) {
  const edit = get(existingWatchersEdit);
  if (!edit[watcher.identifier]) {
    // If we're not in edit mode, just go into edit mode
    changeEditMode(watcher.identifier);
  }
  else {
    // If we're in edit mode, check to see if the values have changed before
    // sending an API call
    const existingWatcherArgs = get(existingWatchers).find(
      existingWatcher => existingWatcher.identifier === watcher.identifier,
    )!.args;
    const modifiedWatcherArgs = watcher.args;

    if (
      existingWatcherArgs.op !== modifiedWatcherArgs.op
      || existingWatcherArgs.ratio !== modifiedWatcherArgs.ratio
    ) {
      try {
        await editWatchers([watcher]);
        validateSettingChange('success', t('watcher_dialog.edit_success'));
        changeEditMode(watcher.identifier);
      }
      catch (error: any) {
        validateSettingChange(
          'error',
          t('watcher_dialog.edit_error', {
            message: error.message,
          }),
        );
      }
    }
    else {
      changeEditMode(watcher.identifier);
    }
  }
}

async function deleteWatcher(identifier: string) {
  try {
    await deleteWatchers([identifier]);
    validateSettingChange('success', t('watcher_dialog.delete_success'));
    clear();
  }
  catch (error: any) {
    validateSettingChange(
      'error',
      t('watcher_dialog.delete_error', {
        message: error.message,
      }),
    );
  }
}

function clear() {
  set(watcherValue, null);
  set(watcherOperation, null);
}

watch(display, (display) => {
  if (display) {
    set(watcherType, get(preselectWatcherType));

    const edit = { ...get(existingWatchersEdit) };
    get(loadedWatchers).forEach((watcher) => {
      edit[watcher.identifier] = false;
    });
    set(existingWatchersEdit, edit);
  }
  else {
    set(watcherType, null);
    set(existingWatchersEdit, {});
  }
});

function cancel() {
  emit('cancel');
  const edit = { ...get(existingWatchersEdit) };
  for (const index in edit) {
    // Reset edit mode on all fields
    edit[index] = false;
  }
  // Reset unsaved changes to the current saved state
  set(existingWatchersEdit, edit);
  clear();
}

const [CreateLabel, ReuseLabel] = createReusableTemplate<{ label: string }>();
</script>

<template>
  <RuiDialog
    :value="display"
    persistent
    max-width="650"
    class="watcher-dialog"
  >
    <CreateLabel #default="{ label }">
      <div class="flex justify-center items-center gap-4">
        <RuiDivider class="flex-grow" />
        <div class="text-center">
          {{ label }}
        </div>
        <RuiDivider class="flex-grow" />
      </div>
    </CreateLabel>

    <RuiCard>
      <template #header>
        {{ title }}
      </template>
      <template #subheader>
        {{ message }}
      </template>

      <RuiMenuSelect
        v-if="!preselectWatcherType"
        v-model="watcherType"
        :options="watcherTypes"
        :label="t('watcher_dialog.labels.type')"
        key-attr="value"
        text-attr="text"
        full-width
        show-details
        dense
        variant="outlined"
        required
      />

      <div class="flex flex-col gap-6">
        <div
          v-if="loadedWatchers.length > 0"
          class="flex flex-col gap-4"
        >
          <ReuseLabel :label="t('watcher_dialog.edit')" />
          <div
            v-for="(watcher, key) in loadedWatchers"
            :key="key"
            class="flex items-center gap-4"
          >
            <div class="grid grid-cols-2 gap-4">
              <RuiMenuSelect
                v-model="loadedWatchers[key].args.op"
                :options="operations"
                :label="t('watcher_dialog.labels.operation')"
                :disabled="!existingWatchersEdit[watcher.identifier]"
                key-attr="value"
                text-attr="text"
                dense
                full-width
                variant="outlined"
                required
              />

              <RuiTextField
                v-model="loadedWatchers[key].args.ratio"
                :label="watcherValueLabel"
                :disabled="!existingWatchersEdit[watcher.identifier]"
                dense
                color="primary"
                hide-details
                variant="outlined"
              >
                <template #append>
                  {{ t('percentage_display.symbol') }}
                </template>
              </RuiTextField>
            </div>

            <div class="flex items-center gap-2 justify-end">
              <RuiButton
                variant="text"
                icon
                @click="editWatcher(loadedWatchers[key])"
              >
                <RuiIcon
                  :name="existingWatchersIcon(watcher.identifier)"
                  size="20"
                />
              </RuiButton>
              <RuiButton
                variant="text"
                icon
                @click="deleteWatcher(watcher.identifier)"
              >
                <RuiIcon
                  name="delete-bin-5-line"
                  size="20"
                />
              </RuiButton>
            </div>
          </div>
        </div>

        <div class="flex flex-col gap-4">
          <ReuseLabel :label="t('watcher_dialog.add_watcher')" />
          <div class="flex items-center gap-4">
            <div class="grid grid-cols-2 gap-4">
              <RuiMenuSelect
                v-model="watcherOperation"
                :disabled="!watcherType"
                :options="operations"
                :label="t('watcher_dialog.labels.operation')"
                key-attr="value"
                text-attr="text"
                full-width
                dense
                variant="outlined"
                required
              />

              <RuiTextField
                v-model="watcherValue"
                :label="watcherValueLabel"
                color="primary"
                dense
                hide-details
                variant="outlined"
              >
                <template #append>
                  {{ t('percentage_display.symbol') }}
                </template>
              </RuiTextField>
            </div>

            <RuiButton
              :disabled="watcherOperation === null || watcherValue === null"
              variant="text"
              icon
              @click="addWatcher()"
            >
              <RuiIcon name="add-line" />
            </RuiButton>
          </div>
        </div>
      </div>

      <template #footer>
        <RuiAlert
          v-if="validationStatus"
          :type="validationStatus"
        >
          {{ validationMessage }}
        </RuiAlert>
        <div class="grow" />
        <RuiButton
          color="primary"
          class="watcher-dialog__buttons__close mt-4"
          @click="cancel()"
        >
          {{ t('common.actions.close') }}
        </RuiButton>
      </template>
    </RuiCard>
  </RuiDialog>
</template>

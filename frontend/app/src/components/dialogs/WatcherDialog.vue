<script setup lang="ts">
import { cloneDeep } from 'es-toolkit';
import { type Watcher, type WatcherOpTypes, WatcherType } from '@/types/session';
import { useWatchersStore } from '@/store/session/watchers';
import type { RuiIcons } from '@rotki/ui-library';

interface WatcherOperation {
  op: WatcherOpTypes;
  value: WatcherOpTypes;
  text: string;
}

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
    existingWatchers: () => [],
    preselectWatcherType: undefined,
    watcherContentId: undefined,
    watcherValueLabel: 'Watcher Value',
  },
);

const emit = defineEmits<{ (e: 'cancel'): void }>();

const { display, existingWatchers, preselectWatcherType, watcherContentId } = toRefs(props);
const watcherType = ref<typeof WatcherType>();
const watcherOperation = ref<WatcherOpTypes>();
const watcherValue = ref<string>('');
const validationMessage = ref<string>('');
const validationStatus = ref<'success' | 'error' | ''>('');
const existingWatchersEdit = ref<Record<string, boolean>>({});

const { t } = useI18n();

const store = useWatchersStore();
const { watchers } = storeToRefs(store);
const { addWatchers, deleteWatchers, editWatchers } = store;

const loadedWatchers = computed<Watcher[]>(() => {
  const id = get(watcherContentId)?.toString();
  return cloneDeep(get(watchers)).filter(watcher => watcher.args.vaultId === id);
});

const watcherTypes = computed(() => [
  {
    text: t('watcher_dialog.types.make_collateralization_ratio'),
    type: WatcherType,
    value: WatcherType,
  },
]);

const watcherOperations = computed<{ [WatcherType]: WatcherOperation[] }>(() => ({
  makervault_collateralization_ratio: [
    {
      op: 'gt',
      text: t('watcher_dialog.ratio.gt'),
      value: 'gt',
    },
    {
      op: 'ge',
      text: t('watcher_dialog.ratio.ge'),
      value: 'ge',
    },
    {
      op: 'lt',
      text: t('watcher_dialog.ratio.lt'),
      value: 'lt',
    },
    {
      op: 'le',
      text: t('watcher_dialog.ratio.le'),
      value: 'le',
    },
  ],
}));

const operations = computed<WatcherOperation[]>(() => {
  const operations = get(watcherOperations);
  const type = get(watcherType);
  if (!type)
    return [];

  return operations[type] ?? [];
});

function existingWatchersIcon(identifier: string): RuiIcons {
  const edit = get(existingWatchersEdit);
  return edit[identifier] ? 'lu-check' : 'lu-pencil';
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
    args: {
      op: operation,
      ratio: value,
      vaultId: contentId.toString(),
    },
    type,
  };

  try {
    await addWatchers([watcherData]);
    validateSettingChange('success', t('watcher_dialog.add_success'));
    clear();
  }
  catch (error: any) {
    validateSettingChange('error', t('watcher_dialog.add_error', { message: error.message }));
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

    if (existingWatcherArgs.op !== modifiedWatcherArgs.op || existingWatcherArgs.ratio !== modifiedWatcherArgs.ratio) {
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
    :model-value="display"
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
                hide-details
                variant="outlined"
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
                  name="lu-trash-2"
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
                dense
                hide-details
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
              <RuiIcon name="lu-plus" />
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

<script setup lang="ts">
import { type ComputedRef, type Ref } from 'vue';
import { cloneDeep } from 'lodash-es';
import {
  type Watcher,
  type WatcherOpTypes,
  WatcherType
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
    existingWatchers: () => []
  }
);

const emit = defineEmits<{ (e: 'cancel'): void }>();

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
  return edit[identifier] ? 'check-line' : 'pencil-line';
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

const [CreateLabel, ReuseLabel] = createReusableTemplate<{ label: string }>();
const percent = '%';
</script>

<template>
  <VDialog
    :value="display"
    persistent
    max-width="650"
    class="watcher-dialog"
    @keydown.esc.stop="cancel()"
  >
    <CreateLabel #default="{ label }">
      <div class="flex justify-center items-center gap-4">
        <RuiDivider class="flex-grow" />
        <div class="text-center">{{ label }}</div>
        <RuiDivider class="flex-grow" />
      </div>
    </CreateLabel>

    <RuiCard>
      <template #header> {{ title }} </template>
      <template #subheader>{{ message }}</template>

      <VSelect
        v-if="!preselectWatcherType"
        v-model="watcherType"
        :items="watcherTypes"
        :label="t('watcher_dialog.labels.type')"
        dense
        outlined
        required
      />

      <div v-if="loadedWatchers.length > 0" class="flex flex-col gap-4">
        <ReuseLabel :label="t('watcher_dialog.edit')" />
        <div
          v-for="(watcher, key) in loadedWatchers"
          :key="key"
          class="flex items-center gap-4"
        >
          <div class="grid grid-cols-2 gap-4">
            <VSelect
              :class="{
                'bg-rui-grey-100 dark:bg-rui-grey-800':
                  !existingWatchersEdit[watcher.identifier]
              }"
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

            <RuiTextField
              :class="{
                'bg-rui-grey-100 dark:bg-rui-grey-800':
                  !existingWatchersEdit[watcher.identifier]
              }"
              :label="watcherValueLabel"
              :readonly="!existingWatchersEdit[watcher.identifier]"
              :value="loadedWatchers[key].args.ratio"
              dense
              color="primary"
              hide-details
              variant="outlined"
              @input="loadedWatchers[key].args.ratio = $event"
            >
              <template #append>{{ percent }}</template>
            </RuiTextField>
          </div>

          <div class="flex items-center gap-2 justify-end">
            <RuiButton
              variant="text"
              size="sm"
              icon
              @click="editWatcher(loadedWatchers[key])"
            >
              <RuiIcon :name="existingWatchersIcon(watcher.identifier)" />
            </RuiButton>
            <RuiButton
              variant="text"
              icon
              size="sm"
              @click="deleteWatcher(watcher.identifier)"
            >
              <RuiIcon name="delete-bin-5-line" />
            </RuiButton>
          </div>
        </div>
      </div>

      <div class="flex flex-col gap-4 mt-4">
        <ReuseLabel :label="t('watcher_dialog.add_watcher')" />
        <div class="flex items-center justify-between gap-4">
          <div class="grid grid-cols-2 gap-4">
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

            <RuiTextField
              v-model="watcherValue"
              :label="watcherValueLabel"
              color="primary"
              dense
              hide-details
              variant="outlined"
            >
              <template #append> {{ percent }} </template>
            </RuiTextField>
          </div>

          <RuiButton
            :disabled="watcherOperation === null || watcherValue === null"
            variant="text"
            icon
            size="sm"
            @click="addWatcher()"
          >
            <RuiIcon name="add-line" />
          </RuiButton>
        </div>
      </div>

      <template #footer>
        <div class="text-caption flex-grow py-2 px-4 mb-4">
          {{ validationMessage }}
        </div>
        <RuiButton
          color="primary"
          class="watcher-dialog__buttons__close"
          @click="cancel()"
        >
          {{ t('common.actions.close') }}
        </RuiButton>
      </template>
    </RuiCard>
  </VDialog>
</template>

<script lang="ts" setup>
import type {
  GroupEventData,
  StandaloneEventData,
} from '@/modules/history/management/forms/form-types';
import BigDialog from '@/components/dialogs/BigDialog.vue';
import HistoryEventForm from '@/components/history/events/HistoryEventForm.vue';

const modelValue = defineModel<GroupEventData | StandaloneEventData | undefined>({ required: true });

withDefaults(defineProps<HistoryEventFormDialogProps>(), {
  loading: false,
});

const emit = defineEmits<{
  refresh: [];
}>();

interface HistoryEventFormDialogProps {
  loading?: boolean;
}

const { t } = useI18n({ useScope: 'global' });

const stateUpdated = ref<boolean>(false);
const loading = ref<boolean>(false);
const form = useTemplateRef<InstanceType<typeof HistoryEventForm>>('form');
const showErrors = ref<boolean>(false);

const errorCount = computed<number>(() => {
  if (!get(showErrors))
    return 0;
  return get(form)?.errorCount ?? 0;
});

const title = computed<string>(() => {
  const value = get(modelValue);
  if (value === undefined || value.type === 'add' || value.type === 'group-add') {
    return t('transactions.events.dialog.add.title');
  }
  return t('transactions.events.dialog.edit.title');
});

async function save(): Promise<void> {
  set(loading, true);
  const success = await get(form)?.save();
  set(loading, false);

  if (success) {
    set(modelValue, undefined);
    set(showErrors, false);
    emit('refresh');
  }
  else {
    set(showErrors, true);
  }
}

watch(modelValue, (value) => {
  if (!isDefined(value)) {
    set(showErrors, false);
  }
});
</script>

<template>
  <BigDialog
    :display="modelValue !== undefined"
    :title="title"
    :primary-action="t('common.actions.save')"
    :action-disabled="loading"
    :loading="loading"
    :prompt-on-close="stateUpdated"
    :error-count="errorCount"
    auto-scroll-to-error
    @confirm="save()"
    @cancel="modelValue = undefined"
  >
    <HistoryEventForm
      v-if="modelValue"
      ref="form"
      v-model:state-updated="stateUpdated"
      :data="modelValue"
    />
  </BigDialog>
</template>

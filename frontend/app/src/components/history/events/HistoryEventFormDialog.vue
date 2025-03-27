<script lang="ts" setup>
import type {
  DependentEventData,
  IndependentEventData,
} from '@/modules/history/management/forms/form-types';
import BigDialog from '@/components/dialogs/BigDialog.vue';
import HistoryEventForm from '@/components/history/events/HistoryEventForm.vue';
import { useHistoryEventsForm } from '@/composables/history/events/form';
import { useTemplateRef } from 'vue';

const modelValue = defineModel<DependentEventData | IndependentEventData | undefined>({ required: true });

withDefaults(defineProps<HistoryEventFormDialogProps>(), {
  loading: false,
});

const emit = defineEmits<{
  refresh: [];
}>();

interface HistoryEventFormDialogProps {
  loading?: boolean;
}

const { defaultNotes } = useHistoryEventsForm();

const { t } = useI18n();

const stateUpdated = ref<boolean>(false);
const loading = ref<boolean>(false);
const form = useTemplateRef<InstanceType<typeof HistoryEventForm>>('form');

const title = computed<string>(() =>
  get(modelValue) !== undefined
    ? t('transactions.events.dialog.edit.title')
    : t('transactions.events.dialog.add.title'),
);

watchImmediate(modelValue, (data) => {
  if (data?.type !== 'edit' || !('defaultNotes' in data.event)) {
    return;
  }
  set(defaultNotes, data.event.defaultNotes);
});

async function save() {
  set(loading, true);
  const success = await get(form)?.save();
  set(loading, false);

  if (success) {
    set(modelValue, undefined);
    emit('refresh');
  }
}
</script>

<template>
  <BigDialog
    :display="modelValue !== undefined"
    :title="title"
    :primary-action="t('common.actions.save')"
    :action-disabled="loading"
    :loading="loading"
    :prompt-on-close="stateUpdated"
    @confirm="save()"
    @cancel="modelValue = undefined"
  >
    <HistoryEventForm
      v-if="modelValue"
      ref="form"
      v-model:state-updated="stateUpdated"
      :data="modelValue"
      :default-notes="defaultNotes"
    />
  </BigDialog>
</template>

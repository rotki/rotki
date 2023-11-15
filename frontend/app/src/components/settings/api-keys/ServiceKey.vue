<script setup lang="ts">
const props = withDefaults(
  defineProps<{
    apiKey: string;
    name: string;
    loading?: boolean;
    tooltip?: string;
    hint?: string;
    label?: string;
    status?: { message: string; success?: boolean };
  }>(),
  {
    status: undefined,
    loading: false,
    tooltip: '',
    hint: '',
    label: ''
  }
);

const emit = defineEmits<{
  (e: 'delete-key', value: string): void;
  (e: 'save', value: { name: string; apiKey: string }): void;
}>();

const { t } = useI18n();
const { apiKey, status } = toRefs(props);

const currentValue = ref<string | null>(null);
const editMode = ref<boolean>(false);
const cancellable = ref<boolean>(false);

const errorMessages = useRefMap(status, status => {
  if (!status || status.success) {
    return [];
  }
  return [status.message];
});

const successMessages = useRefMap(status, status => {
  if (!status || !status.success) {
    return [];
  }
  return [status.message];
});

const updateStatus = () => {
  if (!get(apiKey)) {
    set(cancellable, false);
    set(editMode, true);
  } else {
    set(cancellable, true);
    set(editMode, false);
  }
  set(currentValue, get(apiKey));
};

const saveHandler = () => {
  if (get(editMode)) {
    emit('save', {
      name: props.name,
      apiKey: get(currentValue)!
    });
    set(editMode, false);
    set(cancellable, true);
  } else {
    set(editMode, true);
  }
};

const cancel = () => {
  set(editMode, false);
  set(currentValue, get(apiKey));
};

onMounted(() => {
  updateStatus();
});

watch(apiKey, () => {
  updateStatus();
});

const slots = useSlots();
</script>

<template>
  <div class="flex flex-col gap-4">
    <div class="flex items-start gap-4" data-cy="service-key__content">
      <RuiRevealableTextField
        v-model="currentValue"
        variant="outlined"
        color="primary"
        class="grow"
        data-cy="service-key__api-key"
        :text-color="!editMode ? 'success' : undefined"
        :error-messages="errorMessages"
        :success-messages="successMessages"
        :hint="currentValue ? '' : hint"
        :disabled="!editMode"
        :label="label"
        prepend-icon="key-line"
      />

      <RuiTooltip :open-delay="400" :popper="{ placement: 'top' }">
        <template #activator>
          <RuiButton
            icon
            variant="text"
            data-cy="service-key__delete"
            class="mt-1"
            :disabled="loading || !apiKey"
            color="primary"
            @click="emit('delete-key', name)"
          >
            <RuiIcon name="delete-bin-line" />
          </RuiButton>
        </template>
        {{ tooltip }}
      </RuiTooltip>
    </div>

    <slot v-if="slots.default" />

    <div class="pt-4 flex gap-2" data-cy="service-key__buttons">
      <RuiButton
        v-if="editMode && cancellable"
        data-cy="service-key__cancel"
        variant="outlined"
        color="primary"
        @click="cancel()"
      >
        {{ t('common.actions.cancel') }}
      </RuiButton>

      <RuiButton
        data-cy="service-key__save"
        color="primary"
        :disabled="(editMode && !currentValue) || loading"
        @click="saveHandler()"
      >
        {{ editMode ? t('common.actions.save') : t('common.actions.edit') }}
      </RuiButton>
    </div>
  </div>
</template>

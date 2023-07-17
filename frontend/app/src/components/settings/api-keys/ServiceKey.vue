<script setup lang="ts">
const props = withDefaults(
  defineProps<{
    value: string;
    title?: string;
    description?: string;
    loading?: boolean;
    tooltip?: string;
    hint?: string;
    label?: string;
  }>(),
  {
    title: '',
    description: '',
    loading: false,
    tooltip: '',
    hint: '',
    label: ''
  }
);

const emit = defineEmits<{
  (e: 'delete-key'): void;
  (e: 'save', value: string): void;
}>();

const { t } = useI18n();
const { value } = toRefs(props);

const deleteKey = () => emit('delete-key');
const save = (value: string) => emit('save', value);

const currentValue = ref<string | null>(null);
const editMode = ref<boolean>(false);
const cancellable = ref<boolean>(false);

const onPaste = (event: ClipboardEvent) => {
  const paste = trimOnPaste(event);
  if (paste) {
    set(currentValue, paste);
  }
};

const updateStatus = () => {
  if (!get(value)) {
    set(cancellable, false);
    set(editMode, true);
  } else {
    set(cancellable, true);
    set(editMode, false);
  }
  set(currentValue, get(value));
};

const saveHandler = () => {
  if (get(editMode)) {
    save(get(currentValue)!);
    set(editMode, false);
    set(cancellable, true);
  } else {
    set(editMode, true);
  }
};

const cancel = () => {
  set(editMode, false);
  set(currentValue, get(value));
};

onMounted(() => {
  updateStatus();
});

watch(value, () => {
  updateStatus();
});
</script>

<template>
  <VCard flat>
    <VCardTitle v-if="title">
      {{ title }}
    </VCardTitle>
    <VCardSubtitle v-if="description">
      {{ description }}
    </VCardSubtitle>
    <VCardText class="service-key__content">
      <VRow justify="center">
        <VCol>
          <RevealableInput
            outlined
            sensitive-key
            :value="editMode ? currentValue : ''"
            class="service-key__api-key"
            :hint="currentValue ? '' : hint"
            :disabled="!editMode"
            :label="label"
            @input="currentValue = $event"
            @paste="onPaste($event)"
          />
        </VCol>
        <VCol cols="auto">
          <VTooltip top>
            <template #activator="{ on }">
              <VBtn
                icon
                text
                class="service-key__content__delete"
                :disabled="loading || !currentValue"
                color="primary"
                v-on="on"
                @click="deleteKey()"
              >
                <VIcon>mdi-delete</VIcon>
              </VBtn>
            </template>
            <span>
              {{ tooltip }}
            </span>
          </VTooltip>
        </VCol>
      </VRow>
      <VRow v-if="$slots.default">
        <VCol>
          <slot />
        </VCol>
      </VRow>
    </VCardText>
    <VCardActions class="service-key__buttons">
      <VBtn
        class="service-key__buttons__save"
        depressed
        color="primary"
        :disabled="(editMode && currentValue === '') || loading"
        @click="saveHandler()"
      >
        {{ editMode ? t('common.actions.save') : t('common.actions.edit') }}
      </VBtn>
      <VBtn
        v-if="editMode && cancellable"
        class="service-key__buttons__cancel"
        depressed
        color="primary"
        @click="cancel()"
      >
        {{ t('common.actions.cancel') }}
      </VBtn>
    </VCardActions>
  </VCard>
</template>

<style scoped lang="scss">
.service-key {
  &__buttons {
    padding: 16px !important;
  }

  &__content {
    &__delete {
      margin-top: 10px;
    }
  }
}
</style>

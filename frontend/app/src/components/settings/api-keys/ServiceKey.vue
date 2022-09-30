<template>
  <v-card flat>
    <v-card-title>
      {{ title }}
    </v-card-title>
    <v-card-subtitle>
      {{ description }}
    </v-card-subtitle>
    <v-card-text class="service-key__content">
      <v-row justify="center">
        <v-col>
          <revealable-input
            outlined
            :value="editMode ? currentValue : ''"
            class="service-key__api-key"
            :hint="currentValue ? '' : hint"
            :disabled="!editMode"
            :label="label"
            @input="currentValue = $event"
            @paste="onPaste"
          />
        </v-col>
        <v-col cols="auto">
          <v-tooltip top>
            <template #activator="{ on }">
              <v-btn
                icon
                text
                class="service-key__content__delete"
                :disabled="loading || !currentValue"
                color="primary"
                v-on="on"
                @click="deleteKey()"
              >
                <v-icon>mdi-delete</v-icon>
              </v-btn>
            </template>
            <span>
              {{ tooltip }}
            </span>
          </v-tooltip>
        </v-col>
      </v-row>
      <v-row v-if="$slots.default">
        <v-col>
          <slot />
        </v-col>
      </v-row>
    </v-card-text>
    <v-card-actions class="service-key__buttons">
      <v-btn
        class="service-key__buttons__save"
        depressed
        color="primary"
        :disabled="(editMode && currentValue === '') || loading"
        @click="saveHandler()"
      >
        {{ editMode ? t('common.actions.save') : t('common.actions.edit') }}
      </v-btn>
      <v-btn
        v-if="editMode && cancellable"
        class="service-key__buttons__cancel"
        depressed
        color="primary"
        @click="cancel()"
      >
        {{ t('common.actions.cancel') }}
      </v-btn>
    </v-card-actions>
  </v-card>
</template>

<script setup lang="ts">
import RevealableInput from '@/components/inputs/RevealableInput.vue';
import { trimOnPaste } from '@/utils/event';

const props = defineProps({
  value: { required: true, type: String },
  title: { required: true, type: String },
  description: { required: false, type: String, default: '' },
  loading: { required: false, type: Boolean, default: false },
  tooltip: { required: false, type: String, default: '' },
  hint: { required: false, type: String, default: '' },
  label: { required: false, type: String, default: '' }
});

const emit = defineEmits(['input', 'delete-key', 'save']);

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

<style scoped lang="scss">
.service-key {
  &__buttons {
    padding: 16px !important;
  }

  &__content {
    &__delete {
      margin-top: 10px;
    }

    :deep() {
      .v-input {
        &--is-disabled {
          .v-icon,
          .v-label {
            color: green !important;
          }
        }
      }
    }
  }
}
</style>

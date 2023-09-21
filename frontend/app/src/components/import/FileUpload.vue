<script setup lang="ts">
import { type PropType } from 'vue';
import { type ImportSourceType, SOURCES } from '@/types/upload-types';

const props = defineProps({
  source: {
    required: true,
    type: String as PropType<ImportSourceType>,
    validator: (value: ImportSourceType) => SOURCES.includes(value)
  },
  loading: { required: false, type: Boolean, default: false },
  fileFilter: { required: false, type: String, default: '.csv' },
  uploaded: { required: false, type: Boolean, default: false },
  errorMessage: { required: false, type: String, default: '' }
});

const emit = defineEmits(['selected', 'update:uploaded']);
const { source, fileFilter, uploaded, errorMessage } = toRefs(props);

const error = ref('');
const active = ref(false);
const file = ref<File | null>(null);
const select = ref<HTMLInputElement>();
const { count, inc, dec, reset } = useCounter(0, { min: 0 });
const { t } = useI18n();

const onDrop = (event: DragEvent) => {
  event.preventDefault();
  set(active, false);
  if (!event.dataTransfer?.files?.length) {
    return;
  }

  if (get(source) !== 'icon') {
    check(event.dataTransfer.files);
  } else {
    selected(event.dataTransfer.files[0]);
  }
};

const onEnter = (event: DragEvent) => {
  event.preventDefault();
  inc();
  set(active, true);
};

const onLeave = (event: DragEvent) => {
  event.preventDefault();
  dec();
  if (get(count) === 0) {
    set(active, false);
  }
};

const onSelect = (event: Event) => {
  const target = event.target as HTMLInputElement;
  if (!target || !target.files) {
    return;
  }
  if (!['icon', 'zip', 'csv', 'json'].includes(get(source))) {
    check(target.files);
  } else {
    selected(target.files[0]);
  }
};

const onError = (message: string) => {
  set(error, message);
  reset();
  set(active, false);
  removeFile();
};

const removeFile = () => {
  const inputFile = get(select);
  if (inputFile) {
    inputFile.value = '';
  }
  set(file, null);
};

const check = (files: FileList) => {
  if (get(error) || get(uploaded)) {
    return;
  }

  if (files.length !== 1) {
    onError(t('file_upload.many_files_selected').toString());
    return;
  }

  if (!files[0].name.endsWith(get(fileFilter))) {
    onError(
      t('file_upload.only_files', {
        fileFilter: get(fileFilter)
      }).toString()
    );
    return;
  }

  set(file, files[0]);
};

const selected = (selected: File | null) => {
  set(file, selected);
  emit('selected', selected);
};

const updateUploaded = (value: boolean) => {
  emit('update:uploaded', value);
};

const clickSelect = () => {
  get(select)?.click();
};

watch(file, file => {
  selected(file);
});

watch(uploaded, uploaded => {
  if (!uploaded) {
    return;
  }
  set(file, null);
  setTimeout(() => {
    updateUploaded(false);
  }, 4000);
});

watch(errorMessage, message => onError(message));

defineExpose({ removeFile });
</script>

<template>
  <VRow>
    <VCol>
      <div
        class="file-upload__drop"
        :class="active ? 'file-upload__drop--active' : null"
        @dragover.prevent
        @drop="onDrop($event)"
        @dragenter="onEnter($event)"
        @dragleave="onLeave($event)"
      >
        <div v-if="error" class="flex flex-col items-center justify-center">
          <VBtn icon small class="self-end" @click="error = ''">
            <VIcon>mdi-close</VIcon>
          </VBtn>
          <VIcon x-large color="error">mdi-alert-circle</VIcon>
          <span class="error--text mt-2">{{ error }}</span>
        </div>
        <div
          v-else-if="loading"
          class="flex flex-col items-center justify-center py-2"
        >
          <VProgressCircular indeterminate color="primary" />

          <div class="pt-4">
            {{ t('file_upload.loading') }}
          </div>
        </div>
        <div
          v-else-if="!uploaded"
          class="flex flex-col items-center justify-center"
        >
          <VIcon x-large color="primary">mdi-upload</VIcon>
          <input
            ref="select"
            type="file"
            :accept="fileFilter"
            hidden
            @change="onSelect($event)"
          />
          <div class="mt-2 text-center">
            <div v-if="file">
              <i18n
                path="file_upload.selected_file"
                class="text-caption text--secondary"
                tag="div"
              >
                <template #name>
                  <div class="font-bold text-truncate">
                    {{ file.name }}
                  </div>
                </template>
              </i18n>
              <div>
                <VBtn
                  class="mt-2"
                  color="primary"
                  small
                  text
                  outlined
                  @click="clickSelect()"
                >
                  {{ t('file_upload.change_file') }}
                </VBtn>
              </div>
            </div>
            <div v-else>
              <div class="text-caption text--secondary">
                {{ t('file_upload.drop_area') }}
              </div>
              <div>
                <VBtn
                  class="mt-2"
                  color="primary"
                  small
                  text
                  outlined
                  @click="clickSelect()"
                >
                  {{ t('file_upload.select_file') }}
                </VBtn>
              </div>
            </div>
          </div>
        </div>
        <div v-else class="flex flex-col items-center justify-center">
          <VIcon x-large color="primary">mdi-check-circle</VIcon>
          <div class="mt-2" v-text="t('file_upload.import_complete')" />
        </div>
      </div>
    </VCol>
  </VRow>
</template>

<style scoped lang="scss">
.file-upload {
  &__drop {
    padding: 12px;
    border: var(--v-rotki-light-grey-darken1) solid thin;
    width: 100%;
    border-radius: 4px;

    &--active {
      background-color: var(--v-rotki-light-grey-darken1);
    }
  }
}

.theme {
  &--dark {
    .file-upload {
      &__drop {
        border-color: var(--v-rotki-light-grey-lighten2);
      }
    }
  }
}
</style>

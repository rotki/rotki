<script setup lang="ts">
import { type ImportSourceType } from '@/types/upload-types';

const props = withDefaults(
  defineProps<{
    value: File | null;
    source: ImportSourceType;
    loading?: boolean;
    fileFilter?: string;
    uploaded?: boolean;
    errorMessage?: string;
  }>(),
  {
    loading: false,
    fileFilter: '.csv',
    uploaded: false,
    errorMessage: ''
  }
);

const emit = defineEmits<{
  (e: 'input', file: File | null): void;
  (e: 'update:uploaded', uploaded: boolean): void;
  (e: 'update:error-message', message: string): void;
}>();
const { source, fileFilter, uploaded, errorMessage } = toRefs(props);

const file = useVModel(props, 'value', emit, { eventName: 'input' });

const error = ref('');
const active = ref(false);
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

const clearError = () => {
  set(error, '');
  emit('update:error-message', '');
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
};

const updateUploaded = (value: boolean) => {
  emit('update:uploaded', value);
};

const clickSelect = () => {
  get(select)?.click();
};

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
</script>

<template>
  <div class="flex flex-row">
    <div
      class="pa-4 border border-default rounded-md w-full"
      :class="{ 'border-primary': active }"
      @dragover.prevent
      @drop="onDrop($event)"
      @dragenter="onEnter($event)"
      @dragleave="onLeave($event)"
    >
      <div class="flex flex-col items-center justify-center">
        <template v-if="error">
          <RuiButton variant="text" class="self-end" icon @click="clearError()">
            <RuiIcon name="close-line" />
          </RuiButton>
          <RuiIcon size="48" name="error-warning-line" color="error" />
          <span class="text-rui-error mt-2">{{ error }}</span>
        </template>

        <template v-else-if="loading">
          <RuiProgress
            circular
            variant="indeterminate"
            color="primary"
            size="24"
          />

          <div class="pt-4">
            {{ t('file_upload.loading') }}
          </div>
        </template>

        <template v-else-if="!uploaded">
          <RuiIcon name="file-upload-line" color="primary" />
          <input
            ref="select"
            type="file"
            :accept="fileFilter"
            hidden
            @change="onSelect($event)"
          />
          <div
            class="flex flex-col mt-2 text-center justify-center text-caption text--secondary w-full"
          >
            <template v-if="file">
              <i18n path="file_upload.selected_file" tag="div">
                <template #name>
                  <div class="font-bold text-truncate">
                    {{ file.name }}
                  </div>
                </template>
              </i18n>
              <RuiButton
                class="mt-2"
                color="primary"
                variant="outlined"
                @click="clickSelect()"
              >
                {{ t('file_upload.change_file') }}
              </RuiButton>
            </template>
            <template v-else>
              {{ t('file_upload.drop_area') }}
              <div class="h-5" />
              <RuiButton
                class="mt-2"
                color="primary"
                variant="outlined"
                @click="clickSelect()"
              >
                {{ t('file_upload.select_file') }}
              </RuiButton>
            </template>
          </div>
        </template>

        <template v-else>
          <RuiIcon name="checkbox-circle-line" color="primary" />
          <div class="mt-2" v-text="t('file_upload.import_complete')" />
        </template>
      </div>
    </div>
  </div>
</template>

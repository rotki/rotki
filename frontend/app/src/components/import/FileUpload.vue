<script setup lang="ts">
import type { ImportSourceType } from '@/types/upload-types';
import FadeTransition from '@/components/helper/FadeTransition.vue';
import { size } from '@/utils/data';

const file = defineModel<File | undefined>({ required: true });

const props = withDefaults(
  defineProps<{
    source: ImportSourceType;
    loading?: boolean;
    fileFilter?: string;
    uploaded?: boolean;
    errorMessage?: string;
  }>(),
  {
    errorMessage: '',
    fileFilter: '.csv',
    loading: false,
    uploaded: false,
  },
);

const emit = defineEmits<{
  (e: 'update:uploaded', uploaded: boolean): void;
  (e: 'update:error-message', message: string): void;
}>();
const { errorMessage, fileFilter, source, uploaded } = toRefs(props);

const wrapper = ref<HTMLDivElement>();

const error = ref('');
const select = ref<HTMLInputElement>();
const { t } = useI18n({ useScope: 'global' });

function isValidFile(file: File, acceptString: string) {
  // Extract the file extension
  const fileName = file.name;
  const fileExtension = fileName.substring(fileName.lastIndexOf('.')).toLowerCase();

  // Extract the file MIME type
  const fileType = file.type;

  // Parse the accept string
  const acceptTypes = acceptString.split(',').map(type => type.trim().toLowerCase());

  // Check if the file extension or MIME type matches any of the accepted types
  for (const type of acceptTypes) {
    if (type === fileExtension || type === fileType || (type === 'image/*' && fileType.startsWith('image/')))
      return true;
  }
  return false;
}

function onDrop(files: File[] | null) {
  if (!files || files.length === 0)
    return;

  check(files);
}

const { isOverDropZone } = useDropZone(wrapper, {
  onDrop,
});

function onSelect(event: Event) {
  const target = event.target as HTMLInputElement;
  if (!target || !target.files)
    return;

  if (!['icon', 'zip', 'csv', 'json'].includes(get(source)))
    check(target.files);
  else selected(target.files[0]);
}

function clearTimeoutHandler(timeout: Ref<NodeJS.Timeout | undefined>) {
  const timeoutVal = get(timeout);
  if (timeoutVal) {
    clearTimeout(timeoutVal);
    set(timeout, undefined);
  }
}

const errorTimeout = ref<NodeJS.Timeout>();
const uploadedTimeout = ref<NodeJS.Timeout>();

function onError(message: string) {
  if (!message) {
    clearError();
    return;
  }

  clearTimeoutHandler(errorTimeout);
  clearTimeoutHandler(uploadedTimeout);

  removeFile();
  set(error, message);
  const timeout = setTimeout(() => {
    clearError();
  }, 4000);
  set(errorTimeout, timeout);
}

function clearError() {
  set(error, '');
  emit('update:error-message', '');
}

function removeFile() {
  const inputFile = get(select);
  if (inputFile)
    inputFile.value = '';

  set(file, null);
}

function check(files: File[] | FileList) {
  if (files.length !== 1) {
    onError(t('file_upload.many_files_selected'));
    return;
  }

  const filter = get(fileFilter);

  if (!isValidFile(files[0], filter)) {
    onError(
      t('file_upload.only_files', {
        fileFilter: filter,
      }),
    );
    return;
  }

  selected(files[0]);
}

function selected(selected: File | null) {
  set(file, selected);
  updateUploaded(false);
  clearError();
}

function updateUploaded(value: boolean) {
  emit('update:uploaded', value);
}

function clickSelect() {
  get(select)?.click();
}

watch(uploaded, (uploaded) => {
  clearTimeoutHandler(errorTimeout);
  clearTimeoutHandler(uploadedTimeout);

  if (!uploaded)
    return;

  removeFile();

  const timeout = setTimeout(() => {
    updateUploaded(false);
  }, 4000);

  set(uploadedTimeout, timeout);
});

watch(errorMessage, message => onError(message));

watch(file, (file) => {
  if (!file) {
    removeFile();
  }
});

function formatFileFilter(fileFilter: string) {
  return fileFilter
    .split(',')
    .map((item) => {
      let text = item.trim();
      if (text.startsWith('.'))
        text = text.slice(1);

      return text;
    })
    .join(', ');
}

defineExpose({
  removeFile,
});
</script>

<template>
  <div class="flex flex-row overflow-hidden">
    <div
      ref="wrapper"
      class="p-4 border border-rui-grey-300 dark:border-rui-grey-800 rounded-md w-full relative border-dashed transition"
      :class="{
        '!border-rui-primary bg-rui-primary/[0.08]': isOverDropZone,
        '!border-rui-error !border-solid bg-rui-error/[0.08]': error,
        '!border-rui-success !border-solid bg-rui-success/[0.08]': uploaded,
      }"
    >
      <div
        class="flex flex-col items-center justify-center"
        :class="{
          'opacity-0': loading,
        }"
      >
        <div class="h-10 bg-rui-primary/[0.12] rounded-full flex items-center justify-center max-w-full overflow-hidden">
          <div class="w-10 h-10 min-w-[10] flex items-center justify-center">
            <RuiIcon
              name="lu-file-up"
              color="primary"
            />
          </div>
          <FadeTransition>
            <div
              v-if="file"
              key="file"
              class="flex items-center gap-2 ml-1 flex-1 overflow-hidden"
            >
              <div class="flex-1 overflow-hidden">
                <div
                  class="text-subtitle-1 !text-sm !leading-5 text-truncate"
                  :title="file.name"
                >
                  {{ file.name }}
                </div>
                <div class="text-rui-text-secondary text-xs !leading-3">
                  {{ size(file.size) }}
                </div>
              </div>
              <RuiButton
                type="button"
                variant="text"
                icon
                @click="removeFile()"
              >
                <RuiIcon
                  name="lu-x"
                  size="16"
                />
              </RuiButton>
            </div>
          </FadeTransition>
        </div>

        <div class="font-bold text-subtitle-1 pt-4">
          <i18n-t
            scope="global"
            keypath="file_upload.drag_and_drop"
            tag="div"
            class="flex justify-center"
          >
            <template #button>
              <RuiButton
                variant="text"
                class="!py-0 px-0.5 -ml-0.5 underline !text-base"
                color="primary"
                @click="clickSelect()"
              >
                {{ file ? t('file_upload.replace_file') : t('file_upload.click_to_upload') }}
              </RuiButton>
            </template>
          </i18n-t>

          <div class="text-body-2 text-center font-normal">
            <div
              v-if="uploaded"
              class="text-rui-success"
            >
              {{ t('file_upload.import_complete') }}
            </div>
            <div
              v-else-if="error"
              class="text-rui-error"
            >
              {{ error }}
            </div>
            <div
              v-else
              class="uppercase text-rui-text-secondary"
            >
              {{ formatFileFilter(fileFilter) }}
            </div>
          </div>
        </div>

        <input
          ref="select"
          type="file"
          :accept="fileFilter"
          hidden
          @change="onSelect($event)"
        />
      </div>

      <div
        v-if="loading"
        class="flex flex-col items-center justify-center absolute h-full w-full top-0 left-0"
      >
        <RuiProgress
          circular
          variant="indeterminate"
          color="primary"
          size="24"
        />

        <div class="pt-4">
          {{ t('file_upload.loading') }}
        </div>
      </div>
    </div>
  </div>
</template>

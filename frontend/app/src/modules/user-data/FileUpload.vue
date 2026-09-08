<script setup lang="ts">
import type { ImportSourceType } from '@/modules/core/common/upload-types';
import { size } from '@/modules/core/common/data/data';
import FadeTransition from '@/modules/shell/components/FadeTransition.vue';
import { checkFiles, formatFileFilter, useFileUploadFeedback } from '@/modules/user-data/use-file-upload';

const file = defineModel<File | undefined>({ required: true });

const {
  errorMessage = '',
  fileFilter = '.csv',
  source,
  uploaded = false,
} = defineProps<{
  source: ImportSourceType;
  loading?: boolean;
  fileFilter?: string;
  uploaded?: boolean;
  errorMessage?: string;
}>();

const emit = defineEmits<{
  'update:uploaded': [uploaded: boolean];
  'update:error-message': [message: string];
}>();

const wrapper = useTemplateRef<HTMLDivElement>('wrapper');

const select = useTemplateRef<HTMLInputElement>('select');
const { t } = useI18n({ useScope: 'global' });

function onDrop(files: File[] | null) {
  if (!files || files.length === 0)
    return;

  check(files);
}

const { isOverDropZone } = useDropZone(wrapper, {
  onDrop,
});

function onSelect(event: Event) {
  const { target } = event;
  if (!(target instanceof HTMLInputElement) || !target.files)
    return;

  if (!['icon', 'zip', 'csv', 'json'].includes(source))
    check(target.files);
  else selected(target.files[0]);
}

const { acknowledgeUpload, clearError, error, showError } = useFileUploadFeedback({
  onErrorCleared: () => emit('update:error-message', ''),
  onUploadedCleared: () => updateUploaded(false),
  removeFile: () => removeFile(),
});

function removeFile() {
  const inputFile = get(select);
  if (inputFile)
    inputFile.value = '';

  set(file, null);
}

function check(files: File[] | FileList) {
  const result = checkFiles(files, fileFilter);

  if (result.valid) {
    selected(result.file);
    return;
  }

  showError(result.reason === 'many-files'
    ? t('file_upload.many_files_selected')
    : t('file_upload.only_files', { fileFilter }));
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

watch(() => uploaded, acknowledgeUpload);

watch(() => errorMessage, message => showError(message));

watch(file, (file) => {
  if (!file) {
    removeFile();
  }
});

defineExpose({
  removeFile,
});
</script>

<template>
  <div class="flex overflow-hidden">
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
              data-testid="import-complete"
            >
              {{ t('file_upload.import_complete') }}
            </div>
            <div
              v-else-if="error"
              class="text-rui-error"
              data-testid="import-error"
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
          data-testid="file-input"
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

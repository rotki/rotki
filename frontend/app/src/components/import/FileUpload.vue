<template>
  <v-row>
    <v-col>
      <div
        class="file-upload__drop"
        :class="active ? 'file-upload__drop--active' : null"
        @dragover.prevent
        @drop="onDrop"
        @dragenter="onEnter"
        @dragleave="onLeave"
      >
        <div
          v-if="error"
          class="d-flex flex-column align-center justify-center"
        >
          <v-btn icon small class="align-self-end" @click="error = ''">
            <v-icon>mdi-close</v-icon>
          </v-btn>
          <v-icon x-large color="error">mdi-alert-circle</v-icon>
          <span class="error--text mt-2">{{ error }}</span>
        </div>
        <div
          v-else-if="loading"
          class="d-flex flex-column align-center justify-center py-2"
        >
          <v-progress-circular indeterminate color="primary" />

          <div class="pt-4">
            {{ $t('file_upload.loading') }}
          </div>
        </div>
        <div
          v-else-if="!uploaded"
          class="d-flex flex-column align-center justify-center"
        >
          <v-icon x-large color="primary">mdi-upload</v-icon>
          <input
            ref="select"
            type="file"
            :accept="fileFilter"
            hidden
            @change="onSelect"
          />
          <div class="mt-2 text-center">
            <div v-if="file">
              <i18n
                path="file_upload.selected_file"
                class="text-caption text--secondary"
                tag="div"
              >
                <template #name>
                  <div class="font-weight-bold text-truncate">
                    {{ file.name }}
                  </div>
                </template>
              </i18n>
              <div>
                <v-btn
                  class="mt-2"
                  color="primary"
                  small
                  text
                  outlined
                  @click="$refs.select.click()"
                  v-text="$t('file_upload.change_file')"
                />
              </div>
            </div>
            <div v-else>
              <div class="text-caption text--secondary">
                {{ $t('file_upload.drop_area') }}
              </div>
              <div>
                <v-btn
                  class="mt-2"
                  color="primary"
                  small
                  text
                  outlined
                  @click="$refs.select.click()"
                  v-text="$t('file_upload.select_file')"
                />
              </div>
            </div>
          </div>
        </div>
        <div v-else class="d-flex flex-column align-center justify-center">
          <v-icon x-large color="primary">mdi-check-circle</v-icon>
          <div class="mt-2" v-text="$t('file_upload.import_complete')" />
        </div>
      </div>
    </v-col>
  </v-row>
</template>

<script lang="ts">
import {
  defineComponent,
  PropType,
  ref,
  toRefs,
  watch
} from '@vue/composition-api';
import { get, set, useCounter } from '@vueuse/core';
import i18n from '@/i18n';

const SOURCES = [
  'cointracking.info',
  'cryptocom',
  'icon',
  'zip',
  'csv',
  'nexo',
  'blockfi-transactions',
  'blockfi-trades',
  'shapeshift-trades',
  'uphold',
  'bisq',
  'binance'
] as const;

export default defineComponent({
  name: 'FileUpload',
  props: {
    source: {
      required: true,
      type: String as PropType<typeof SOURCES[number]>,
      validator: (value: typeof SOURCES[number]) => {
        return SOURCES.includes(value);
      }
    },
    loading: { required: false, type: Boolean, default: false },
    fileFilter: { required: false, type: String, default: '.csv' },
    uploaded: { required: false, type: Boolean, default: false },
    errorMessage: { required: false, type: String, default: '' }
  },
  emits: ['selected'],
  setup(props, { emit }) {
    const { source, fileFilter, uploaded, errorMessage } = toRefs(props);

    const error = ref('');
    const active = ref(false);
    const file = ref<File | null>(null);
    const select = ref<HTMLInputElement>();
    const { count, inc, dec, reset } = useCounter(0, { min: 0 });

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
      if (!['icon', 'zip', 'csv'].includes(get(source))) {
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
        onError(i18n.t('file_upload.many_files_selected').toString());
        return;
      }

      if (!files[0].name.endsWith('.csv')) {
        onError(
          i18n
            .t('file_upload.only_files', {
              fileFilter: get(fileFilter)
            })
            .toString()
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

    return {
      file,
      error,
      active,
      select,
      onDrop,
      onEnter,
      onLeave,
      onSelect,
      removeFile
    };
  }
});
</script>

<style scoped lang="scss">
.file-upload {
  &__drop {
    padding: 12px;
    border: var(--v-rotki-light-grey-darken1) solid thin;
    width: 100%;
    border-radius: 4px;

    &--active {
      background-color: #f9f9f9;
    }
  }
}

.theme {
  &--dark {
    .file-upload {
      &__drop {
        border: thin solid rgba(255, 255, 255, 0.12);
      }
    }
  }
}
</style>

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
                path="file_upload.inputted_file"
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
import { Component, Emit, Prop, Vue, Watch } from 'vue-property-decorator';

const SOURCES = [
  'cointracking.info',
  'cryptocom',
  'icon',
  'nexo',
  'blockfi-transactions',
  'blockfi-trades',
  'gitcoin',
  'shapeshift-trades',
  'uphold',
  'bisq'
];

@Component({})
export default class FileUpload extends Vue {
  @Prop({
    required: true,
    type: String,
    validator: value => SOURCES.includes(value)
  })
  source!: string;
  @Prop({ required: false, default: '.csv' })
  fileFilter!: string;

  @Emit()
  selected(_file: File) {}

  error: string = '';
  active: boolean = false;
  count: number = 0;
  uploaded: boolean = false;

  file: File | null = null;

  done() {
    this.uploaded = true;
    setTimeout(() => {
      this.uploaded = false;
    }, 4000);
  }

  onDrop(event: DragEvent) {
    event.preventDefault();
    this.active = false;
    if (!event.dataTransfer?.files?.length) {
      return;
    }

    if (this.source !== 'icon') {
      this.check(event.dataTransfer.files);
    } else {
      this.selected(event.dataTransfer.files[0]);
    }
  }

  onEnter(event: DragEvent) {
    event.preventDefault();
    this.count++;
    this.active = true;
  }

  onLeave(event: DragEvent) {
    event.preventDefault();
    this.count--;

    if (this.count === 0) {
      this.active = false;
    }
  }

  onSelect(event: Event) {
    const target = event.target as HTMLInputElement;
    if (!target || !target.files) {
      return;
    }
    if (this.source !== 'icon') {
      this.check(target.files);
    } else {
      this.selected(target.files[0]);
    }
  }

  onError(message: string) {
    this.error = message;
    this.count = 0;
    this.active = false;
    this.removeFile();
  }

  removeFile() {
    const inputFile = this.$refs.select as any;
    if (inputFile) {
      inputFile.value = null;
    }
    this.file = null;
  }

  @Watch('file')
  onFileChange(file: File) {
    this.selected(file);
  }

  check(files: FileList) {
    if (this.error || this.uploaded) {
      return;
    }

    if (files.length !== 1) {
      this.onError(this.$tc('file_upload.many_files_selected'));
      return;
    }

    if (!files[0].name.endsWith('.csv')) {
      this.onError(
        this.$t('file_upload.only_files', {
          fileFilter: this.fileFilter
        }).toString()
      );
      return;
    }

    this.file = files[0];
  }
}
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

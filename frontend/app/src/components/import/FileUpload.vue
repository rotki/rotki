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
          <i18n
            path="file_upload.drop_area"
            class="mt-2 text-caption text--secondary d-flex flex-column text-center"
            tag="div"
          >
            <v-btn
              class="mt-2"
              color="primary"
              small
              text
              outlined
              @click="$refs.select.click()"
              v-text="$t('file_upload.select_file')"
            />
          </i18n>
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
import { Component, Emit, Prop, Vue } from 'vue-property-decorator';

const SOURCES = [
  'cointracking.info',
  'cryptocom',
  'icon',
  'nexo',
  'blockfi-transactions',
  'blockfi-trades',
  'gitcoin'
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
  uploaded = false;

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
      this.upload(event.dataTransfer.files);
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
      this.upload(target.files);
    } else {
      this.selected(target.files[0]);
    }
  }

  onError(message: string) {
    this.error = message;
    this.count = 0;
    this.active = false;
  }

  async uploadPackaged(file: string) {
    try {
      await this.$api.importDataFrom(this.source, file);
      this.done();
    } catch (e) {
      this.onError(e.message);
    }
  }

  upload(files: FileList) {
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

    if (this.$interop.isPackaged && this.$api.defaultBackend) {
      this.uploadPackaged(files[0].path);
    } else {
      const formData = new FormData();
      formData.append('source', this.source);
      formData.append('file', files[0]);
      this.$api
        .importFile(formData)
        .catch(({ message }) => this.onError(message))
        .then(this.done);
    }
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

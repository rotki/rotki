<template>
  <div>
    <div>
      <div class="mb-2">
        <slot name="upload-title" />
      </div>
      <v-form ref="form" v-model="valid">
        <file-upload
          ref="fileUploadInput"
          :source="source"
          @selected="upload($event)"
        />
        <v-switch
          :value="dateInputFormat !== null"
          @change="changeShouldCustomDateFormat"
        >
          <template #label>
            {{ $t('file_upload.date_input_format.switch_label') }}
          </template>
        </v-switch>
        <v-text-field
          v-if="dateInputFormat !== null"
          v-model="dateInputFormat"
          class="mt-2"
          outlined
          :rules="dateFormatRules"
          :placeholder="$t('file_upload.date_input_format.placeholder')"
          :hint="
            $t('file_upload.date_input_format.hint', {
              format: dateInputFormatExample
            })
          "
          persistent-hint
        >
          <template #append>
            <v-btn small icon @click="formatHelp = true">
              <v-icon small> mdi-information </v-icon>
            </v-btn>
          </template>
        </v-text-field>

        <div class="mt-4">
          <v-row>
            <v-col cols="12">
              <slot />
            </v-col>
          </v-row>
          <v-row v-if="$slots.hint">
            <v-col cols="12">
              <slot name="hint" />
            </v-col>
          </v-row>
        </div>
        <div class="mt-6">
          <v-btn
            color="primary"
            depressed
            block
            data-cy="button-import"
            :disabled="!valid || !file"
            @click="uploadFile"
          >
            {{ $t('file_upload.import') }}
          </v-btn>
        </div>
      </v-form>
    </div>
    <date-format-help v-model="formatHelp" />
  </div>
</template>

<script lang="ts">
import { computed, defineComponent, ref, toRefs } from '@vue/composition-api';
import FileUpload from '@/components/import/FileUpload.vue';
import { displayDateFormatter } from '@/data/date_formatter';
import { interop } from '@/electron-interop';
import i18n from '@/i18n';
import { api } from '@/services/rotkehlchen-api';
import { DateFormat } from '@/types/date-format';
import DateFormatHelp from '@/views/settings/DateFormatHelp.vue';

export default defineComponent({
  name: 'ImportSource',
  components: { DateFormatHelp, FileUpload },
  props: {
    icon: {
      required: false,
      default: '',
      type: String
    },
    source: { required: true, type: String }
  },
  setup(props) {
    const { source } = toRefs(props);
    const dateInputFormat = ref<string | null>(null);
    const fileUploadInput = ref(null);
    const valid = ref<boolean>(true);
    const formatHelp = ref<boolean>(false);
    const file = ref<File | null>(null);

    const upload = (selectedFile: File) => {
      file.value = selectedFile;
    };

    const dateFormatRules = [
      (v: string) => {
        if (!v) {
          return i18n.t('general_settings.date_display.validation.empty');
        }
        if (!displayDateFormatter.containsValidDirectives(v)) {
          return i18n
            .t('general_settings.date_display.validation.invalid')
            .toString();
        }
        return true;
      }
    ];

    const dateInputFormatExample = computed(() => {
      const now = new Date();
      if (!dateInputFormat.value) return '';
      return displayDateFormatter.format(now, dateInputFormat.value);
    });

    const uploadPackaged = async (file: string) => {
      const fileInput: FileUpload = fileUploadInput.value!;
      try {
        await api.importDataFrom(
          source.value,
          file,
          dateInputFormat.value || null
        );
        fileInput?.done();
      } catch (e: any) {
        fileInput?.onError(e.message);
      }
    };

    const uploadFile = () => {
      const fileInput: FileUpload = fileUploadInput.value!;

      if (file.value) {
        if (interop.isPackaged && api.defaultBackend) {
          uploadPackaged(file.value.path);
        } else {
          const formData = new FormData();
          formData.append('source', source.value);
          formData.append('file', file.value);
          if (dateInputFormat.value) {
            formData.append('timestamp_format', dateInputFormat.value);
          }
          api
            .importFile(formData)
            .catch(({ message }) => fileInput.onError(message))
            .then(fileInput.done);
        }
      }
    };

    const changeShouldCustomDateFormat = () => {
      if (dateInputFormat.value === null) {
        dateInputFormat.value = DateFormat.DateMonthYearHourMinuteSecond;
      } else {
        dateInputFormat.value = null;
      }
    };

    return {
      fileUploadInput,
      dateInputFormat,
      dateFormatRules,
      dateInputFormatExample,
      valid,
      formatHelp,
      upload,
      uploadFile,
      file,
      changeShouldCustomDateFormat
    };
  }
});
</script>

<style module lang="scss">
.image {
  padding: 10px;
  max-width: 200px;
}
</style>

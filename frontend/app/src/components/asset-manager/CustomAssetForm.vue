<template>
  <v-form :value="valid">
    <v-row class="mt-2">
      <v-col cols="12" md="6">
        <v-text-field
          data-cy="name"
          :value="value.name"
          outlined
          persistent-hint
          clearable
          :label="t('common.name')"
          :error-messages="v$.name.$errors.map(e => e.$message)"
          @input="input({ name: $event })"
        />
      </v-col>
      <v-col cols="12" md="6">
        <v-combobox
          data-cy="type"
          :items="types"
          :value="value.customAssetType"
          outlined
          persistent-hint
          clearable
          :label="t('common.type')"
          :error-messages="v$.type.$errors.map(e => e.$message)"
          :search-input.sync="search"
          @input="input({ customAssetType: $event })"
        />
      </v-col>
      <v-col cols="12">
        <v-textarea
          data-cy="notes"
          :value="value.notes"
          outlined
          persistent-hint
          clearable
          :label="t('asset_form.labels.notes')"
          @input="input({ notes: $event })"
        />
      </v-col>
    </v-row>
  </v-form>
</template>
<script setup lang="ts">
import useVuelidate from '@vuelidate/core';
import { helpers, required } from '@vuelidate/validators';
import { PropType } from 'vue';
import { CustomAsset } from '@/types/assets';

const props = defineProps({
  value: {
    required: true,
    type: Object as PropType<CustomAsset>
  },
  edit: {
    required: true,
    type: Boolean
  },
  types: {
    required: true,
    type: Array as PropType<string[]>
  }
});

const emit = defineEmits<{
  (e: 'input', form: Partial<CustomAsset>): void;
  (e: 'valid', valid: boolean): void;
}>();

const { value } = toRefs(props);
const valid = ref(false);

const input = (asset: Partial<CustomAsset>) => {
  emit('input', { ...get(value), ...asset });
};

watch(valid, value => emit('valid', value));

const { t } = useI18n();

const search = ref<string | null>('');

watch(search, customAssetType => {
  if (customAssetType === null) customAssetType = '';
  input({ customAssetType });
});

const rules = {
  name: {
    required: helpers.withMessage(
      t('asset_form.name_non_empty').toString(),
      required
    )
  },
  type: {
    required: helpers.withMessage(
      t('asset_form.type_non_empty').toString(),
      required
    )
  }
};

const v$ = useVuelidate(
  rules,
  {
    name: computed(() => get(value).name),
    type: computed(() => get(value).customAssetType)
  },
  { $autoDirty: true }
);

watch(v$, ({ $invalid }) => {
  set(valid, !$invalid);
});
</script>

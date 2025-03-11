<script setup lang="ts">
import type { Tag } from '@/types/tags';
import TagIcon from '@/components/tags/TagIcon.vue';
import { useFormStateWatcher } from '@/composables/form';
import { useRefPropVModel } from '@/utils/model';
import { toMessages } from '@/utils/validation';
import { invertColor, randomColor } from '@rotki/common';
import useVuelidate from '@vuelidate/core';
import { helpers, required } from '@vuelidate/validators';

const modelValue = defineModel<Tag>({ required: true });

const stateUpdated = defineModel<boolean>('stateUpdated', { required: true });

defineProps<{
  editMode: boolean;
}>();

const { t } = useI18n();

const name = useRefPropVModel(modelValue, 'name');
const description = useRefPropVModel(modelValue, 'description');
const backgroundColor = useRefPropVModel(modelValue, 'backgroundColor');
const foregroundColor = useRefPropVModel(modelValue, 'foregroundColor');

useFormStateWatcher({
  backgroundColor,
  description,
  foregroundColor,
  name,
}, stateUpdated);

const rules = {
  description: {
    optional: () => true,
  },
  name: {
    required: helpers.withMessage(t('tag_creator.validation.empty_name'), required),
  },
};

const v$ = useVuelidate(
  rules,
  {
    description,
    name,
  },
  { $autoDirty: true },
);

function randomize() {
  const newBgColor = randomColor();
  const newFgColor = invertColor(newBgColor);
  set(modelValue, {
    ...get(modelValue),
    backgroundColor: newBgColor,
    foregroundColor: newFgColor,
  });
}

defineExpose({
  validate: async (): Promise<boolean> => await get(v$).$validate(),
});
</script>

<template>
  <div class="flex flex-col gap-2 py-2">
    <RuiCard
      variant="outlined"
      class="overflow-hidden mb-2"
      content-class="flex justify-between items-center"
    >
      <template #custom-header>
        <div class="bg-rui-grey-100 dark:bg-rui-grey-800 text-rui-text-secondary px-4 py-2 font-medium text-sm">
          {{ t('tag_creator.tag_view') }}
        </div>
      </template>
      <TagIcon
        class="min-w-[7rem] min-h-8"
        :tag="modelValue"
      />
      <RuiButton
        size="sm"
        variant="text"
        color="primary"
        @click="randomize()"
      >
        <template #prepend>
          <RuiIcon name="lu-shuffle" />
        </template>
        {{ t('tag_creator.shuffle') }}
      </RuiButton>
    </RuiCard>
    <RuiTextField
      v-model="name"
      variant="outlined"
      color="primary"
      class="tag_creator__name"
      data-cy="tag-creator-name"
      :label="t('common.name')"
      :error-messages="toMessages(v$.name)"
      :disabled="editMode"
    />
    <RuiTextField
      v-model="description"
      variant="outlined"
      color="primary"
      class="tag_creator__description"
      data-cy="tag-creator-description"
      :label="t('common.description')"
    />

    <RuiDivider class="mb-4" />

    <div class="grid md:grid-cols-2 gap-4">
      <RuiCard class="flex flex-col items-center">
        <template #header>
          {{ t('tag_creator.labels.foreground') }}
        </template>
        <RuiColorPicker
          v-model="foregroundColor"
          class="w-full"
          data-cy="tag-creator__color-picker__foreground"
        />
      </RuiCard>
      <RuiCard class="flex flex-col items-center">
        <template #header>
          {{ t('tag_creator.labels.background') }}
        </template>
        <RuiColorPicker
          v-model="backgroundColor"
          class="w-full"
          data-cy="tag-creator__color-picker__background"
        />
      </RuiCard>
    </div>
  </div>
</template>

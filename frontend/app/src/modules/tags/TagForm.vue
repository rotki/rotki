<script setup lang="ts">
import type { ZodType } from 'zod';
import type { Tag } from '@/modules/tags/tags';
import { invertColor, randomColor } from '@rotki/common';
import { useModelForm } from '@/modules/core/form/use-model-form';
import { tagSchema } from '@/modules/tags/tag-forms';
import TagIcon from '@/modules/tags/TagIcon.vue';

const modelValue = defineModel<Tag>({ required: true });

const stateUpdated = defineModel<boolean>('stateUpdated', { required: true });

const { t } = useI18n({ useScope: 'global' });

const schema = computed<ZodType>(() => tagSchema({
  name: t('tag_creator.validation.empty_name'),
}));

const form = useModelForm<Tag>({
  model: modelValue,
  schema,
  stateUpdated,
});

/** The column is nullable, and a description of only spaces is stored as no description at all. */
const descriptionModel = computed<string>({
  get() {
    return form.state.description || '';
  },
  set(value: string) {
    const trimmed = value.trim();
    form.state.description = trimmed.length > 0 ? trimmed : null;
  },
});

function randomize(): void {
  const background = randomColor();
  form.state.backgroundColor = background;
  form.state.foregroundColor = invertColor(background);
}

defineExpose({
  validate: (): boolean => form.validate(),
});
</script>

<template>
  <div class="flex flex-col gap-2 py-2">
    <RuiCard
      variant="outlined"
      class="overflow-hidden mb-2"
      :class-names="{ content: 'flex justify-between items-center' }"
    >
      <template #custom-header>
        <div class="bg-rui-grey-100 dark:bg-rui-grey-800 text-rui-text-secondary px-4 py-2 font-medium text-sm">
          {{ t('tag_creator.tag_view') }}
        </div>
      </template>
      <TagIcon
        class="min-w-[7rem] min-h-8"
        :tag="form.state"
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
      v-model="form.state.name"
      variant="outlined"
      color="primary"
      data-testid="tag-creator-name"
      :label="t('common.name')"
      :error-messages="form.errors('name')"
      @update:model-value="form.touch('name')"
    />
    <RuiTextField
      v-model="descriptionModel"
      variant="outlined"
      color="primary"
      data-testid="tag-creator-description"
      :label="t('common.description')"
    />

    <RuiDivider class="mb-4" />

    <div class="grid md:grid-cols-2 gap-4">
      <RuiCard class="flex flex-col items-center">
        <template #header>
          {{ t('tag_creator.labels.foreground') }}
        </template>
        <RuiColorPicker
          v-model="form.state.foregroundColor"
          class="w-full"
          data-testid="tag-creator-color-picker-foreground"
        />
      </RuiCard>
      <RuiCard class="flex flex-col items-center">
        <template #header>
          {{ t('tag_creator.labels.background') }}
        </template>
        <RuiColorPicker
          v-model="form.state.backgroundColor"
          class="w-full"
          data-testid="tag-creator-color-picker-background"
        />
      </RuiCard>
    </div>
  </div>
</template>

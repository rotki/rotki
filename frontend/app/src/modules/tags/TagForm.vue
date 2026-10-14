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
  <div class="flex flex-col gap-4 py-2">
    <div
      class="flex items-center justify-between gap-4 rounded-rui-control border border-rui-divider bg-rui-grey-50 dark:bg-rui-grey-900 px-4 py-3"
      data-testid="tag-creator-preview"
    >
      <div class="flex items-center gap-3 min-w-0">
        <span class="text-body-2 text-rui-text-secondary shrink-0">{{ t('tag_creator.tag_view') }}</span>
        <TagIcon
          class="min-w-20"
          :tag="form.state"
        />
      </div>
      <RuiButton
        size="sm"
        variant="text"
        color="primary"
        class="shrink-0"
        @click="randomize()"
      >
        <template #prepend>
          <RuiIcon name="lu-shuffle" />
        </template>
        {{ t('tag_creator.shuffle') }}
      </RuiButton>
    </div>
    <RuiTextField
      v-model="form.state.name"
      color="primary"
      data-testid="tag-creator-name"
      :label="t('common.name')"
      :error-messages="form.errors('name')"
      @update:model-value="form.touch('name')"
    />
    <RuiTextField
      v-model="descriptionModel"
      color="primary"
      data-testid="tag-creator-description"
      :label="t('common.description')"
      hide-details
    />

    <div class="grid md:grid-cols-2 gap-6 pt-2">
      <section class="flex flex-col gap-2">
        <h3 class="text-body-2 font-medium text-rui-text m-0">
          {{ t('tag_creator.labels.foreground') }}
        </h3>
        <RuiColorPicker
          v-model="form.state.foregroundColor"
          class="w-full"
          data-testid="tag-creator-color-picker-foreground"
        />
      </section>
      <section class="flex flex-col gap-2">
        <h3 class="text-body-2 font-medium text-rui-text m-0">
          {{ t('tag_creator.labels.background') }}
        </h3>
        <RuiColorPicker
          v-model="form.state.backgroundColor"
          class="w-full"
          data-testid="tag-creator-color-picker-background"
        />
      </section>
    </div>
  </div>
</template>

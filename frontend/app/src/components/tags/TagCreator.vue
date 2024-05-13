<script setup lang="ts">
import useVuelidate from '@vuelidate/core';
import { helpers, required } from '@vuelidate/validators';
import { toMessages } from '@/utils/validation';
import type { Tag, TagEvent } from '@/types/tags';

const props = defineProps<{
  tag: Tag;
  editMode: boolean;
}>();

const emit = defineEmits<{
  (e: 'update:tag', tag: Tag): void;
  (e: 'save', data: { tag: Tag; close?: boolean }): void;
  (e: 'cancel'): void;
}>();

const { t } = useI18n();

const name = usePropVModel(props, 'tag', 'name', emit);
const description = usePropVModel(props, 'tag', 'description', emit);

const { tag, editMode } = toRefs(props);
const tagPreview = ref();

const rules = {
  name: {
    required: helpers.withMessage(
      t('tag_creator.validation.empty_name'),
      required,
    ),
  },
  description: {
    optional: () => true,
  },
};

const v$ = useVuelidate(
  rules,
  {
    name,
    description,
  },
  { $autoDirty: true },
);

function changed(event: TagEvent) {
  emit('update:tag', {
    ...props.tag,
    ...event,
  });
}

async function save(close?: boolean) {
  const v = get(v$);
  if (!(await v.$validate()))
    return;

  emit('save', { tag: props.tag, close });
}

function cancel() {
  emit('cancel');
}

function randomize() {
  const backgroundColor = randomColor();
  changed({
    backgroundColor,
    foregroundColor: invertColor(backgroundColor),
  });
}

watch(tag, () => {
  get(v$).$reset();
});

watchImmediate(editMode, (edit) => {
  if (edit)
    get(tagPreview).$el.scrollIntoView({ behavior: 'smooth' });
});
</script>

<template>
  <div class="flex flex-col gap-4">
    <div class="flex items-center gap-4">
      <TagIcon
        ref="tagPreview"
        class="[&>div]:min-w-[7rem]"
        :tag="tag"
      />
      <RuiTooltip :popper="{ placement: 'bottom' }">
        <template #activator>
          <RuiButton
            icon
            size="sm"
            variant="text"
            color="primary"
            @click="randomize()"
          >
            <RuiIcon name="shuffle-line" />
          </RuiButton>
        </template>
        {{ t('tag_creator.refresh_tooltip') }}
      </RuiTooltip>
    </div>
    <div class="mt-4">
      <RuiTextField
        v-model="name"
        variant="outlined"
        color="primary"
        class="tag_creator__name"
        :label="t('common.name')"
        :error-messages="toMessages(v$.name)"
        :disabled="editMode"
      />
      <RuiTextField
        v-model="description"
        variant="outlined"
        color="primary"
        class="tag_creator__description"
        :label="t('common.description')"
      />
    </div>
    <div class="grid md:grid-cols-2 gap-4">
      <RuiCard class="flex flex-col items-center">
        <template #header>
          {{ t('tag_creator.labels.foreground') }}
        </template>
        <RuiColorPicker
          class="w-full"
          data-cy="tag-creator__color-picker__foreground"
          :value="tag.foregroundColor"
          @input="changed({ foregroundColor: $event })"
        />
      </RuiCard>
      <RuiCard class="flex flex-col items-center">
        <template #header>
          {{ t('tag_creator.labels.background') }}
        </template>
        <RuiColorPicker
          class="w-full"
          data-cy="tag-creator__color-picker__background"
          :value="tag.backgroundColor"
          @input="changed({ backgroundColor: $event })"
        />
      </RuiCard>
    </div>

    <div class="flex justify-end gap-4">
      <RuiButton
        v-if="editMode"
        width="100"
        @click="cancel()"
      >
        {{ t('common.actions.cancel') }}
      </RuiButton>
      <RuiButton
        data-cy="tag-creator__buttons__save_continue"
        color="primary"
        :disabled="v$.$invalid"
        @click="save()"
      >
        {{ t('common.actions.save_continue') }}
      </RuiButton>
      <RuiButton
        data-cy="tag-creator__buttons__save"
        color="primary"
        :disabled="v$.$invalid"
        @click="save(true)"
      >
        {{ t('common.actions.save') }}
      </RuiButton>
    </div>
  </div>
</template>

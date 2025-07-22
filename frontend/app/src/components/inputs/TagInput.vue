<script setup lang="ts">
import { invertColor, randomColor } from '@rotki/common';
import ListItem from '@/components/common/ListItem.vue';
import TagFormDialog from '@/components/tags/TagFormDialog.vue';
import TagIcon from '@/components/tags/TagIcon.vue';
import { useTagStore } from '@/store/session/tags';
import { defaultTag, type Tag } from '@/types/tags';

const modelValue = defineModel<string[]>({ required: true });

withDefaults(
  defineProps<{
    disabled?: boolean;
    label?: string;
  }>(),
  {
    label: 'Tags',
  },
);

const { t } = useI18n({ useScope: 'global' });
const store = useTagStore();
const { tags } = storeToRefs(store);

const search = ref<string>('');

const newTag = ref<Tag | undefined>(undefined);

const newTagBackground = ref(randomColor());

function remove(tag: string) {
  const tags = get(modelValue);
  const index = tags.indexOf(tag);
  onUpdateModelValue([...tags.slice(0, index), ...tags.slice(index + 1)]);
}

function attemptTagCreation(element: string) {
  store.attemptTagCreation(element, get(newTagBackground))
    .then((success) => {
      if (!success)
        remove(element);
    });
}

function onUpdateModelValue(_value: ({ name: string } | string | Tag)[]) {
  const tags: string[] = [];
  for (const element of _value) {
    if (typeof element === 'string') {
      attemptTagCreation(element);
      tags.push(element);
    }
    else if (!('description' in element)) {
      attemptTagCreation(element.name);
      tags.push(element.name);
    }
    else {
      tags.push(element.name);
    }
  }

  set(modelValue, tags);
}

function handleCreateNewTag() {
  set(newTag, defaultTag());
}

watch(search, (keyword: string | null, previous: string | null) => {
  if (keyword && !previous)
    set(newTagBackground, randomColor());
});

const newTagForeground = computed<string>(() => invertColor(get(newTagBackground)));

const filteredValue = computed<Tag[]>(() => get(tags).filter(({ name }) => get(modelValue).includes(name)));

watch(tags, () => {
  const filtered = get(filteredValue);
  if (get(modelValue).length > filtered.length)
    onUpdateModelValue(filtered);
});
</script>

<template>
  <div class="flex items-start gap-2">
    <RuiAutoComplete
      v-model:search-input="search"
      :model-value="filteredValue"
      :disabled="disabled"
      :options="tags"
      class="tag-input flex-1"
      :hide-no-data="!search"
      :label="label"
      variant="outlined"
      text-attr="name"
      key-attr="name"
      return-object
      custom-value
      clearable
      hide-custom-value
      :item-height="54"
      @update:model-value="onUpdateModelValue($event)"
    >
      <template #no-data>
        <ListItem
          class="p-2 py-4"
          @click="onUpdateModelValue([...filteredValue, search])"
        >
          <template #title>
            <div class="flex items-center gap-4">
              <span>{{ t('common.actions.create') }}</span>

              <TagIcon
                small
                :tag="{
                  name: search,
                  backgroundColor: newTagBackground,
                  foregroundColor: newTagForeground,
                  description: '',
                }"
              />
            </div>
          </template>
        </ListItem>
      </template>
      <template #selection="{ item, chipAttrs }">
        <TagIcon
          small
          :tag="item"
          v-bind="chipAttrs"
          closeable
          :disabled="disabled"
          clickable
        />
      </template>
      <template #item="{ item }">
        <TagIcon
          :tag="item"
          show-description
          small
        />
      </template>
    </RuiAutoComplete>
    <RuiButton
      class="mt-1"
      data-cy="add-tag-button"
      icon
      variant="text"
      color="primary"
      type="button"
      :disabled="disabled"
      @click="handleCreateNewTag()"
    >
      <RuiIcon name="lu-plus" />
    </RuiButton>

    <TagFormDialog v-model="newTag" />
  </div>
</template>

<script setup lang="ts">
import type { Tag } from '@/types/tags';

const props = withDefaults(
  defineProps<{
    value: string[];
    disabled?: boolean;
    label?: string;
  }>(),
  {
    label: 'Tags',
  },
);

const emit = defineEmits<{
  (e: 'input', tags: string[]): void;
}>();

const { t } = useI18n();
const { value } = toRefs(props);
const store = useTagStore();
const { tags } = storeToRefs(store);

const manageTags = ref<boolean>(false);

const search = ref<string>('');

function randomScheme() {
  const backgroundColor = randomColor();
  return {
    backgroundColor,
    foregroundColor: invertColor(backgroundColor),
  };
}

const colorScheme = ref(randomScheme());

function tagExists(tagName: string): boolean {
  return get(tags)
    .map(({ name }) => name)
    .includes(tagName);
}

async function createTag(name: string) {
  const { backgroundColor, foregroundColor } = get(colorScheme);
  const tag: Tag = {
    name,
    description: '',
    backgroundColor,
    foregroundColor,
  };
  return await store.addTag(tag);
}

function remove(tag: string) {
  const tags = get(value);
  const index = tags.indexOf(tag);
  input([...tags.slice(0, index), ...tags.slice(index + 1)]);
}

function attemptTagCreation(element: string) {
  if (tagExists(element))
    return;

  createTag(element)
    .then(({ success }) => {
      if (!success)
        remove(element);
    })
    .catch(error => logger.error(error));
}

function input(_value: ({ name: string } | string | Tag)[]) {
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

  emit('input', tags);
}

watch(search, (keyword: string | null, previous: string | null) => {
  if (keyword && !previous)
    set(colorScheme, randomScheme());
});

const newTagBackground = computed<string>(
  () => `#${get(colorScheme).backgroundColor}`,
);

const newTagForeground = computed<string>(
  () => `#${get(colorScheme).foregroundColor}`,
);

const filteredValue = computed<Tag[]>(() =>
  get(tags).filter(({ name }) => get(value).includes(name)),
);

watch(tags, () => {
  const filtered = get(filteredValue);
  if (get(value).length > filtered.length)
    input(filtered);
});
</script>

<template>
  <div class="flex items-start gap-2">
    <RuiAutoComplete
      :value="filteredValue"
      :disabled="disabled"
      :options="tags"
      class="tag-input flex-1"
      :hide-no-data="!search"
      :label="label"
      variant="outlined"
      :search-input.sync="search"
      text-attr="name"
      key-attr="name"
      return-object
      custom-value
      :item-height="54"
      @input="input($event)"
    >
      <template #no-data>
        <ListItem
          class="p-2 py-4"
          @click="input([...filteredValue, search])"
        >
          <template #title>
            <span>{{ t('common.actions.create') }}</span>
            <RuiChip
              class="ml-3"
              :bg-color="newTagBackground"
              :text-color="newTagForeground"
              tile
              size="sm"
            >
              {{ search }}
            </RuiChip>
          </template>
        </ListItem>
      </template>
      <template #selection="{ item, chipAttrs, chipOn }">
        <RuiChip
          tile
          class="font-medium m-0.5"
          :bg-color="`#${item.backgroundColor}`"
          :text-color="`#${item.foregroundColor}`"
          closeable
          :disabled="disabled"
          clickable
          size="sm"
          v-bind="chipAttrs"
          v-on="chipOn"
        >
          {{ item.name }}
        </RuiChip>
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
      class="tag-input__manage-tags mt-1"
      icon
      variant="text"
      color="primary"
      type="button"
      :disabled="disabled"
      @click="manageTags = true"
    >
      <RuiIcon name="pencil-line" />
    </RuiButton>
    <RuiDialog
      v-model="manageTags"
      max-width="800"
      class="tag-input__tag-manager"
    >
      <TagManager
        dialog
        @close="manageTags = false"
      />
    </RuiDialog>
  </div>
</template>

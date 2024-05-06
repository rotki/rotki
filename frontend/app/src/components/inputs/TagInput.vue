<script setup lang="ts">
import type { Tag } from '@/types/tags';

const props = withDefaults(
  defineProps<{
    value: string[];
    disabled?: boolean;
    label?: string;
    outlined?: boolean;
  }>(),
  {
    label: 'Tags',
    outlined: false,
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

function input(_value: (string | Tag)[]) {
  const tags: string[] = [];
  for (const element of _value) {
    if (typeof element === 'string') {
      attemptTagCreation(element);
      tags.push(element);
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
  <div>
    <VCombobox
      :value="filteredValue"
      :disabled="disabled"
      :items="tags"
      class="tag-input"
      small-chips
      :hide-no-data="!search"
      hide-selected
      :label="label"
      :outlined="outlined"
      :search-input.sync="search"
      item-text="name"
      :menu-props="{ closeOnContentClick: true }"
      item-value="name"
      multiple
      @input="input($event)"
    >
      <template #no-data>
        <ListItem class="p-2">
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
      <template #selection="{ item, select }">
        <RuiChip
          tile
          class="font-medium m-0.5"
          :bg-color="`#${item.backgroundColor}`"
          :text-color="`#${item.foregroundColor}`"
          closeable
          :disabled="disabled"
          size="sm"
          @click:close="remove(item.name)"
          @click="select($event)"
        >
          {{ item.name }}
        </RuiChip>
      </template>
      <template #item="{ item }">
        <template v-if="typeof item !== 'object'">
          {{ item }}
        </template>
        <template v-else>
          <TagIcon
            :tag="item"
            show-description
          />
        </template>
      </template>
      <template #append-outer>
        <RuiButton
          class="tag-input__manage-tags -mt-4"
          icon
          variant="text"
          color="primary"
          type="button"
          :disabled="disabled"
          @click="manageTags = true"
        >
          <RuiIcon name="pencil-line" />
        </RuiButton>
      </template>
    </VCombobox>
    <RuiDialog
      v-model="manageTags"
      max-width="800"
      class="tag-input__tag-manager"
    >
      <AppBridge>
        <TagManager
          dialog
          @close="manageTags = false"
        />
      </AppBridge>
    </RuiDialog>
  </div>
</template>

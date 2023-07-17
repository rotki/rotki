<script setup lang="ts">
import { type PropType } from 'vue';
import { type Tag } from '@/types/tags';

const props = defineProps({
  value: {
    required: true,
    type: Array as PropType<string[]>,
    validator: (value: any) => {
      if (!checkIfDevelopment()) {
        return true;
      }
      if (!Array.isArray(value)) {
        return false;
      }
      return (value as Array<any>).every(
        element => typeof element === 'string'
      );
    }
  },
  disabled: { required: false, type: Boolean, default: false },
  label: { required: false, type: String, default: 'Tags' },
  outlined: { required: false, type: Boolean, default: false }
});

const emit = defineEmits<{
  (e: 'input', tags: string[]): void;
}>();

const { t } = useI18n();
const { value } = toRefs(props);
const store = useTagStore();
const { tags } = storeToRefs(store);

const manageTags = ref<boolean>(false);

const search = ref<string>('');

const randomScheme = () => {
  const backgroundColor = randomColor();
  return {
    backgroundColor,
    foregroundColor: invertColor(backgroundColor)
  };
};

const colorScheme = ref(randomScheme());

const tagExists = (tagName: string): boolean =>
  get(tags)
    .map(({ name }) => name)
    .includes(tagName);

const createTag = async (name: string) => {
  const { backgroundColor, foregroundColor } = get(colorScheme);
  const tag: Tag = {
    name,
    description: '',
    backgroundColor,
    foregroundColor
  };
  return await store.addTag(tag);
};

const remove = (tag: string) => {
  const tags = get(value);
  const index = tags.indexOf(tag);
  input([...tags.slice(0, index), ...tags.slice(index + 1)]);
};

const attemptTagCreation = (element: string) => {
  if (tagExists(element)) {
    return;
  }
  createTag(element)
    .then(({ success }) => {
      if (!success) {
        remove(element);
      }
    })
    .catch(e => logger.error(e));
};

const input = (_value: (string | Tag)[]) => {
  const tags: string[] = [];
  for (const element of _value) {
    if (typeof element === 'string') {
      attemptTagCreation(element);
      tags.push(element);
    } else {
      tags.push(element.name);
    }
  }

  emit('input', tags);
};

watch(search, (keyword: string | null, previous: string | null) => {
  if (keyword && !previous) {
    set(colorScheme, randomScheme());
  }
});

const newTagBackground = computed<string>(
  () => `#${get(colorScheme).backgroundColor}`
);

const newTagForeground = computed<string>(
  () => `#${get(colorScheme).foregroundColor}`
);

const filteredValue = computed<Tag[]>(() =>
  get(tags).filter(({ name }) => get(value).includes(name))
);

watch(tags, () => {
  const filtered = get(filteredValue);
  if (get(value).length > filtered.length) {
    input(filtered);
  }
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
        <VListItem>
          <span class="subheading">{{ t('common.actions.create') }}</span>
          <VChip
            class="ml-2"
            :color="newTagBackground"
            :text-color="newTagForeground"
            label
            small
          >
            {{ search }}
          </VChip>
        </VListItem>
      </template>
      <template #selection="{ item, selected, select }">
        <VChip
          label
          class="font-weight-medium"
          :input-value="selected"
          :color="`#${item.backgroundColor}`"
          :text-color="`#${item.foregroundColor}`"
          close
          @click:close="remove(item.name)"
          @click="select($event)"
        >
          {{ item.name }}
        </VChip>
      </template>
      <template #item="{ item }">
        <template v-if="typeof item !== 'object'">
          <VListItemContent>
            {{ item }}
          </VListItemContent>
        </template>
        <template v-else>
          <div>
            <TagIcon :tag="item" />
            <span class="tag-input__tag__description">
              {{ item.description }}
            </span>
          </div>
        </template>
      </template>
      <template #append-outer>
        <VBtn
          class="tag-input__manage-tags mt-n2"
          icon
          text
          color="primary"
          :disabled="disabled"
          @click="manageTags = true"
        >
          <VIcon>mdi-pencil</VIcon>
        </VBtn>
      </template>
    </VCombobox>
    <VDialog
      :value="manageTags"
      max-width="800"
      class="tag-input__tag-manager"
      content-class="fill-height"
      @input="manageTags = false"
    >
      <TagManager v-if="manageTags" dialog @close="manageTags = false" />
    </VDialog>
  </div>
</template>

<style scoped lang="scss">
.tag-input {
  &__tag {
    &__description {
      padding-left: 18px;
    }
  }
}
</style>

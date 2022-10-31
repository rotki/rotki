<template>
  <div>
    <v-combobox
      :value="values"
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
      @input="input"
    >
      <template #no-data>
        <v-list-item>
          <span class="subheading">{{ t('common.actions.create') }}</span>
          <v-chip
            class="ml-2"
            :color="newTagBackground"
            :text-color="newTagForeground"
            label
            small
          >
            {{ search }}
          </v-chip>
        </v-list-item>
      </template>
      <template #selection="{ item, selected, select }">
        <v-chip
          label
          class="font-weight-medium"
          :input-value="selected"
          :color="`#${item.backgroundColor}`"
          :text-color="`#${item.foregroundColor}`"
          close
          @click:close="remove(item.name)"
          @click="select"
        >
          {{ item.name }}
        </v-chip>
      </template>
      <template #item="{ item }">
        <template v-if="typeof item !== 'object'">
          <v-list-item-content>
            {{ item }}
          </v-list-item-content>
        </template>
        <template v-else>
          <div>
            <tag-icon :tag="item" />
            <span class="tag-input__tag__description">
              {{ item.description }}
            </span>
          </div>
        </template>
      </template>
      <template #append-outer>
        <v-btn
          class="tag-input__manage-tags"
          icon
          text
          color="primary"
          :disabled="disabled"
          @click="manageTags = true"
        >
          <v-icon>mdi-pencil</v-icon>
        </v-btn>
      </template>
    </v-combobox>
    <v-dialog
      :value="!!manageTags"
      max-width="800"
      class="tag-input__tag-manager"
      @input="manageTags = false"
    >
      <tag-manager v-if="!!manageTags" dialog @close="manageTags = false" />
    </v-dialog>
  </div>
</template>

<script setup lang="ts">
import { PropType } from 'vue';
import TagIcon from '@/components/tags/TagIcon.vue';
import TagManager from '@/components/tags/TagManager.vue';
import { useTagStore } from '@/store/session/tags';
import { Tag } from '@/types/user';
import { invertColor, randomColor } from '@/utils/Color';
import { checkIfDevelopment } from '@/utils/env-utils';
import { logger } from '@/utils/logging';

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

const emit = defineEmits(['input']);

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

const tagExists = (tagName: string): boolean => {
  return get(tags)
    .map(({ name }) => name)
    .includes(tagName);
};

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
  for (let i = 0; i < _value.length; i++) {
    const element = _value[i];
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

const newTagBackground = computed<string>(() => {
  return `#${get(colorScheme).backgroundColor}`;
});

const newTagForeground = computed<string>(() => {
  return `#${get(colorScheme).foregroundColor}`;
});

const values = computed<Tag[]>(() => {
  return get(tags).filter(({ name }) => get(value).includes(name));
});
</script>

<style scoped lang="scss">
:deep() {
  .v-dialog {
    &--active {
      height: 100%;
    }
  }

  .v-text-field {
    &--outlined {
      .v-btn {
        &--icon {
          margin-top: -8px;
        }
      }
    }
  }
}

.tag-input {
  &__tag {
    &__description {
      padding-left: 18px;
    }
  }
}
</style>

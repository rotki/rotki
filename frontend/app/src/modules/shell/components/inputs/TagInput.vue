<script setup lang="ts">
import { invertColor, randomColor } from '@rotki/common';
import { startPromise } from '@shared/utils';
import { useFailureMessage } from '@/modules/core/api/use-failure-message';
import { useSessionMetadataStore } from '@/modules/session/use-session-metadata-store';
import ListItem from '@/modules/shell/components/ListItem.vue';
import { renameTagInList } from '@/modules/tags/tag-utils';
import TagFormDialog from '@/modules/tags/TagFormDialog.vue';
import TagIcon from '@/modules/tags/TagIcon.vue';
import { defaultTag, type Tag } from '@/modules/tags/tags';
import { useTagOperations } from '@/modules/tags/use-tag-operations';

const modelValue = defineModel<string[]>({ required: true });

const { disabled, label = 'Tags' } = defineProps<{
  disabled?: boolean;
  label?: string;
}>();

const { t } = useI18n({ useScope: 'global' });
const { tags } = storeToRefs(useSessionMetadataStore());
const { attemptTagCreation: attemptTag } = useTagOperations();
const failureMessage = useFailureMessage();

const search = ref<string>('');

const newTag = ref<Tag | undefined>(undefined);
const editMode = ref<boolean>(false);
const originalName = ref<string>('');

const newTagBackground = ref<string>(randomColor());
/** Why the last inline tag creation failed, shown under the field until the next attempt. */
const creationError = ref<string>('');

function remove(tag: string): void {
  set(modelValue, get(modelValue).filter(name => name !== tag));
}

/** Creates a tag typed into the field; one that cannot be created is named under it and dropped. */
async function attemptTagCreation(element: string): Promise<void> {
  set(creationError, '');
  const result = await attemptTag(element, get(newTagBackground));
  if (result.ok)
    return;
  set(creationError, failureMessage(result.error));
  remove(element);
}

/** Sets the field's tags, then creates the ones typed into it that are not tags yet. */
async function onUpdateModelValue(value: ({ name: string } | string | Tag)[]): Promise<void> {
  const tags: string[] = [];
  const typed: string[] = [];
  for (const element of value) {
    if (typeof element === 'string')
      typed.push(element);
    else if (!('description' in element))
      typed.push(element.name);
    tags.push(typeof element === 'string' ? element : element.name);
  }

  set(modelValue, tags);
  await Promise.all(typed.map(async name => attemptTagCreation(name)));
}

function handleEditTag(tag: Tag): void {
  set(editMode, true);
  set(originalName, tag.name);
  set(newTag, { ...tag });
}

function handleTagSaved(tag: Tag, previousName: string): void {
  if (!previousName || previousName === tag.name)
    return;

  set(modelValue, renameTagInList(get(modelValue), previousName, tag.name));
}

function handleCreateNewTag() {
  set(editMode, false);
  set(originalName, '');
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
    startPromise(onUpdateModelValue(filtered));
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
      :error-messages="creationError"
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
          @click="handleEditTag(item)"
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
    <RuiTooltip
      :options="{ placement: 'top' }"
      :open-delay="400"
    >
      <template #activator>
        <RuiButton
          class="mt-6"
          data-testid="add-tag-button"
          icon
          variant="text"
          color="primary"
          type="button"
          :aria-label="t('tag_manager.create_tag.title')"
          :disabled="disabled"
          @click="handleCreateNewTag()"
        >
          <RuiIcon name="lu-plus" />
        </RuiButton>
      </template>
      {{ t('tag_manager.create_tag.title') }}
    </RuiTooltip>

    <TagFormDialog
      v-model="newTag"
      :edit-mode="editMode"
      :original-name="originalName"
      @saved="handleTagSaved($event.tag, $event.originalName)"
    />
  </div>
</template>

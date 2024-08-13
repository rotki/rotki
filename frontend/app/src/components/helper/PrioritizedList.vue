<script setup lang="ts">
import { EmptyListId, type PrioritizedListId } from '@/types/settings/prioritized-list-id';
import type { Nullable } from '@rotki/common';
import type { BaseMessage } from '@/types/messages';
import type { PrioritizedListData, PrioritizedListItemData } from '@/types/settings/prioritized-list-data';

const props = withDefaults(
  defineProps<{
    modelValue: PrioritizedListId[];
    allItems: PrioritizedListData<PrioritizedListId>;
    itemDataName: string;
    disableAdd?: boolean;
    disableDelete?: boolean;
    status?: BaseMessage;
  }>(),
  {
    disableAdd: false,
    disableDelete: false,
    status: undefined,
  },
);

const emit = defineEmits<{
  (e: 'update:model-value', value: PrioritizedListId[]): void;
}>();
const { allItems, itemDataName } = toRefs(props);
const selection = ref<Nullable<PrioritizedListId>>(null);

const input = (items: PrioritizedListId[]) => emit('update:model-value', items);

const itemNameTr = computed(() => {
  const name = get(itemDataName);
  return {
    name,
    namePluralized: pluralize(name, 2),
  };
});

const missing = computed<PrioritizedListId[]>(() => get(allItems).itemIdsNotIn(props.modelValue));

const noResults = computed<boolean>(() => props.modelValue.length === 0);

const isFirst = (item: string): boolean => props.modelValue[0] === item;

function isLast(item: string): boolean {
  const items = props.modelValue;
  return items.at(-1) === item;
}

function itemData(identifier: PrioritizedListId): PrioritizedListItemData<PrioritizedListId> {
  const data = get(allItems);
  return data.itemDataForId(identifier) ?? { identifier: EmptyListId };
}

function addItem() {
  assert(get(selection));
  const items = [...props.modelValue];
  items.push(get(selection)!);
  input(items);
  set(selection, null);
}

function move(item: PrioritizedListId, down: boolean) {
  const items = [...props.modelValue];
  const itemIndex = items.indexOf(item);
  const nextIndex = itemIndex + (down ? 1 : -1);
  const nextItem = items[nextIndex];
  items[nextIndex] = item;
  items[itemIndex] = nextItem;
  input(items);
}

function remove(item: PrioritizedListId) {
  const items = [...props.modelValue];
  const itemIndex = items.indexOf(item);
  items.splice(itemIndex, 1);
  input(items);
}

const { t } = useI18n();

const autoCompleteHint = computed<string>(() => {
  const num = get(missing).length;
  if (num) {
    return t('prioritized_list.disabled_items', {
      num,
      namePluralized: get(itemNameTr).namePluralized,
    });
  }
  return t('prioritized_list.all_added');
});
</script>

<template>
  <div>
    <RuiCard
      rounded="md"
      no-padding
      class="overflow-hidden"
    >
      <template
        v-if="$slots.title"
        #header
      >
        <slot name="title" />
      </template>

      <div
        v-if="!disableAdd"
        class="flex px-4 py-2 gap-4 items-start border-b border-default"
      >
        <RuiAutoComplete
          v-model="selection"
          variant="outlined"
          :label="t('common.actions.search')"
          :no-data-text="t('prioritized_list.all_added', itemNameTr)"
          :options="missing"
          :item-height="52"
          :hint="autoCompleteHint"
        >
          <template #selection="{ item }">
            <PrioritizedListEntry
              :data="itemData(item)"
              size="24px"
            />
          </template>
          <template #item="{ item }">
            <PrioritizedListEntry
              :data="itemData(item)"
              size="24px"
            />
          </template>
        </RuiAutoComplete>
        <RuiTooltip :open-delay="400">
          <template #activator>
            <RuiButton
              id="add-item-btn"
              color="primary"
              icon
              variant="text"
              class="mt-1"
              :disabled="!selection"
              @click="addItem()"
            >
              <RuiIcon name="add-line" />
            </RuiButton>
          </template>
          <span>
            {{ t('prioritized_list.add_tooltip', itemNameTr) }}
          </span>
        </RuiTooltip>
      </div>
      <SimpleTable variant="default">
        <thead>
          <tr>
            <th class="w-10" />
            <th class="w-8 px-0 text-center">
              {{ t('common.priority') }}
            </th>
            <th class="ps-6">
              {{ t('common.name') }}
            </th>
            <th />
          </tr>
        </thead>
        <tbody v-if="noResults">
          <tr>
            <td colspan="4">
              <div class="flex justify-center p-3 text-h6">
                {{ t('prioritized_list.item.empty', itemNameTr) }}
              </div>
            </td>
          </tr>
        </tbody>
        <TransitionGroup
          v-else
          move-class="transition-all"
          tag="tbody"
        >
          <tr
            v-for="(identifier, index) in modelValue"
            :key="identifier"
            class="odd:bg-rui-grey-50 odd:dark:bg-rui-grey-900"
          >
            <td>
              <div class="flex flex-col">
                <RuiButtonGroup
                  variant="outlined"
                  size="sm"
                  icon
                  vertical
                >
                  <RuiButton
                    :id="`move-up-${identifier}`"
                    class="!px-2"
                    :disabled="isFirst(identifier)"
                    @click="move(identifier, false)"
                  >
                    <RuiIcon name="arrow-up-s-line" />
                  </RuiButton>
                  <RuiButton
                    :id="`move-down-${identifier}`"
                    class="!px-2"
                    :disabled="isLast(identifier)"
                    @click="move(identifier, true)"
                  >
                    <RuiIcon name="arrow-down-s-line" />
                  </RuiButton>
                </RuiButtonGroup>
              </div>
            </td>
            <td class="text-center px-0">
              {{ index + 1 }}
            </td>
            <td>
              <PrioritizedListEntry :data="itemData(identifier)" />
            </td>
            <td class="text-end">
              <RuiTooltip
                v-if="!disableDelete"
                :popper="{ placement: 'top' }"
                :open-delay="400"
              >
                <template #activator>
                  <RuiButton
                    :id="`delete-${identifier}`"
                    icon
                    variant="text"
                    @click="remove(identifier)"
                  >
                    <RuiIcon name="close-line" />
                  </RuiButton>
                </template>
                <span>
                  {{ t('prioritized_list.item.delete', itemNameTr) }}
                </span>
              </RuiTooltip>
            </td>
          </tr>
        </TransitionGroup>
      </SimpleTable>
    </RuiCard>
    <ActionStatusIndicator
      class="my-4"
      :status="status"
    />
  </div>
</template>

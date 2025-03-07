<script setup lang="ts">
import { EmptyListId, type PrioritizedListId } from '@/types/settings/prioritized-list-id';
import ActionStatusIndicator from '@/components/error/ActionStatusIndicator.vue';
import PrioritizedListEntry from '@/components/helper/PrioritizedListEntry.vue';
import SimpleTable from '@/components/common/SimpleTable.vue';
import type { Nullable } from '@rotki/common';
import type { BaseMessage } from '@/types/messages';
import type { PrioritizedListData, PrioritizedListItemData } from '@/types/settings/prioritized-list-data';

const props = withDefaults(
  defineProps<{
    modelValue: PrioritizedListId[];
    allItems: PrioritizedListData<PrioritizedListId>;
    itemDataName?: string;
    disableAdd?: boolean;
    disableDelete?: boolean;
    status?: BaseMessage;
    variant?: 'flat' | 'outlined';
  }>(),
  {
    disableAdd: false,
    disableDelete: false,
    itemDataName: '',
    status: undefined,
    variant: 'outlined',
  },
);

const emit = defineEmits<{
  (e: 'update:model-value', value: PrioritizedListId[]): void;
}>();

defineSlots<{
  default: () => any;
  title: () => any;
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
      namePluralized: get(itemNameTr).namePluralized,
      num,
    });
  }
  return t('prioritized_list.all_added');
});
</script>

<template>
  <RuiCard
    rounded="md"
    no-padding
    :variant="variant"
    class="overflow-hidden [&>div:first-child]:px-6 [&>div:first-child]:pb-2"
  >
    <template
      v-if="$slots.title"
      #header
    >
      <slot name="title" />
    </template>

    <div
      v-if="!disableAdd"
      class="flex px-6 py-2 gap-2 items-start border-b border-default"
    >
      <RuiAutoComplete
        v-model="selection"
        dense
        variant="outlined"
        :label="t('common.actions.search')"
        :no-data-text="t('prioritized_list.all_added', itemNameTr)"
        :options="missing"
        :item-height="36"
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
      <RuiButton
        id="add-item-btn"
        color="primary"
        variant="outlined"
        :disabled="!selection"
        class="h-10"
        @click="addItem()"
      >
        <div class="flex items-center gap-2">
          <RuiIcon name="lu-plus" />
          {{ t('common.actions.add') }}
        </div>
      </RuiButton>
    </div>
    <SimpleTable variant="default">
      <thead>
        <tr>
          <th class="!px-0 w-8" />
          <th class="w-8 !px-0 text-center">
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
          class="odd:bg-rui-grey-50 odd:dark:bg-rui-grey-900 group"
        >
          <td class="!pr-0 !pl-2">
            <div class="flex flex-col gap-1 transition-all opacity-0 invisible group-hover:opacity-100 group-hover:visible">
              <RuiButton
                :id="`move-up-${identifier}`"
                size="sm"
                class="!px-1"
                :disabled="isFirst(identifier)"
                @click="move(identifier, false)"
              >
                <RuiIcon
                  name="lu-arrow-up"
                  size="16"
                />
              </RuiButton>
              <RuiButton
                :id="`move-down-${identifier}`"
                size="sm"
                class="!px-1"
                :disabled="isLast(identifier)"
                @click="move(identifier, true)"
              >
                <RuiIcon
                  name="lu-arrow-down"
                  size="16"
                />
              </RuiButton>
            </div>
          </td>
          <td class="text-center px-0">
            {{ index + 1 }}
          </td>
          <td>
            <PrioritizedListEntry
              :data="itemData(identifier)"
              size="28px"
            />
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
                  class="transition-all opacity-0 invisible group-hover:opacity-100 group-hover:visible"
                  icon
                  variant="text"
                  @click="remove(identifier)"
                >
                  <RuiIcon name="lu-x" />
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
    v-if="status && (status.success || status.error)"
    class="mx-[1px]"
    :status="status"
  />
  <div v-else />
</template>

<script setup lang="ts">
import { type ComputedRef } from 'vue';
import { type Nullable } from '@/types';
import { type BaseMessage } from '@/types/messages';
import {
  type PrioritizedListData,
  type PrioritizedListItemData
} from '@/types/settings/prioritized-list-data';
import {
  EmptyListId,
  type PrioritizedListId
} from '@/types/settings/prioritized-list-id';

const props = withDefaults(
  defineProps<{
    value: PrioritizedListId[];
    allItems: PrioritizedListData<PrioritizedListId>;
    itemDataName: string;
    disableAdd?: boolean;
    disableDelete?: boolean;
    status?: BaseMessage;
  }>(),
  {
    disableAdd: false,
    disableDelete: false,
    status: undefined
  }
);

const emit = defineEmits<{ (e: 'input', value: PrioritizedListId[]): void }>();
const { value, allItems, itemDataName } = toRefs(props);
const slots = useSlots();
const selection = ref<Nullable<PrioritizedListId>>(null);

const input = (items: PrioritizedListId[]) => emit('input', items);

const itemNameTr = computed(() => {
  const name = get(itemDataName);
  return {
    name,
    namePluralized: pluralize(name, 2)
  };
});

const missing = computed<string[]>(() =>
  get(allItems).itemIdsNotIn(get(value))
);

const noResults = computed<boolean>(() => get(value).length === 0);

const isFirst = (item: string): boolean => get(value)[0] === item;

const isLast = (item: string): boolean => {
  const items = get(value);
  return items[items.length - 1] === item;
};

const itemData = (
  identifier: PrioritizedListId
): PrioritizedListItemData<PrioritizedListId> => {
  const data = get(allItems);
  return data.itemDataForId(identifier) ?? { identifier: EmptyListId };
};

const addItem = () => {
  assert(get(selection));
  const items = [...get(value)];
  items.push(get(selection)!);
  input(items);
  set(selection, null);
};

const move = (item: PrioritizedListId, down: boolean) => {
  const items = [...get(value)];
  const itemIndex = items.indexOf(item);
  const nextIndex = itemIndex + (down ? 1 : -1);
  const nextItem = items[nextIndex];
  items[nextIndex] = item;
  items[itemIndex] = nextItem;
  input(items);
};

const remove = (item: PrioritizedListId) => {
  const items = [...get(value)];
  const itemIndex = items.indexOf(item);
  items.splice(itemIndex, 1);
  input(items);
};

const { t } = useI18n();

const autoCompleteHint: ComputedRef<string> = computed(() => {
  const num = get(missing).length;
  if (num) {
    return t('prioritized_list.disabled_items', {
      num,
      namePluralized: get(itemNameTr).namePluralized
    });
  }
  return t('prioritized_list.all_added');
});
</script>

<template>
  <div>
    <RuiCard rounded="md" no-padding>
      <template v-if="slots.title" #header>
        <div class="p-4">
          <slot name="title" />
        </div>
      </template>

      <div
        v-if="!disableAdd"
        class="flex px-4 pb-2 gap-4 items-start border-b border-default"
      >
        <VAutocomplete
          v-model="selection"
          class="grow"
          prepend-inner-icon="mdi-magnify"
          outlined
          :no-data-text="t('prioritized_list.all_added', itemNameTr)"
          :items="missing"
          :hint="autoCompleteHint"
          persistent-hint
        >
          <template #selection="{ item }">
            <PrioritizedListEntry :data="itemData(item)" size="24px" />
          </template>
          <template #item="{ item }">
            <PrioritizedListEntry :data="itemData(item)" size="24px" />
          </template>
        </VAutocomplete>
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
      <VSimpleTable>
        <thead>
          <tr>
            <th class="w-10" />
            <th class="w-[3.75rem] text-center">
              {{ t('common.priority') }}
            </th>
            <th class="ps-6">{{ t('common.name') }}</th>
            <th />
          </tr>
        </thead>
        <tbody>
          <tr v-if="noResults">
            <td colspan="4">
              <div class="flex justify-center pa-3 text-h6">
                {{ t('prioritized_list.item.empty', itemNameTr) }}
              </div>
            </td>
          </tr>
          <tr v-for="(identifier, index) in value" :key="identifier">
            <td>
              <div class="flex flex-col py-2">
                <RuiButtonGroup variant="outlined" size="sm" icon vertical>
                  <template #default>
                    <RuiButton
                      :id="'move-up-' + identifier"
                      :disabled="isFirst(identifier)"
                      @click="move(identifier, false)"
                    >
                      <RuiIcon name="arrow-up-s-line" />
                    </RuiButton>
                    <RuiButton
                      :id="'move-down-' + identifier"
                      :disabled="isLast(identifier)"
                      @click="move(identifier, true)"
                    >
                      <RuiIcon name="arrow-down-s-line" />
                    </RuiButton>
                  </template>
                </RuiButtonGroup>
              </div>
            </td>
            <td class="text-center">{{ index + 1 }}</td>
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
                    :id="'delete-' + identifier"
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
        </tbody>
      </VSimpleTable>
    </RuiCard>
    <ActionStatusIndicator class="my-4" :status="status" />
  </div>
</template>

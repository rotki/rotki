<script setup lang="ts">
import { type ComputedRef, type PropType } from 'vue';
import { type Nullable } from '@/types';
import { type BaseMessage } from '@/types/messages';
import {
  PrioritizedListData,
  type PrioritizedListItemData
} from '@/types/prioritized-list-data';
import {
  EmptyListId,
  type PrioritizedListId
} from '@/types/prioritized-list-id';

const props = defineProps({
  value: { required: true, type: Array as PropType<PrioritizedListId[]> },
  allItems: {
    required: true,
    type: PrioritizedListData<PrioritizedListId>
  },
  itemDataName: { required: true, type: String },
  disableAdd: { required: false, type: Boolean, default: false },
  disableDelete: { required: false, type: Boolean, default: false },
  status: {
    required: false,
    type: Object as PropType<BaseMessage>,
    default: () => null
  }
});

const emit = defineEmits(['input']);
const { value, allItems, itemDataName } = toRefs(props);
const slots = useSlots();
const selection = ref<Nullable<PrioritizedListId>>(null);

const input = (items: string[]) => emit('input', items);

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
    <v-sheet outlined rounded>
      <div class="pb-0" :class="slots.title ? 'pa-4' : 'pa-0'">
        <div v-if="slots.title" class="text-h6 pb-4">
          <slot name="title" />
        </div>

        <v-row v-if="!disableAdd" no-gutters>
          <v-col class="pr-4">
            <v-autocomplete
              v-model="selection"
              prepend-inner-icon="mdi-magnify"
              outlined
              :no-data-text="t('prioritized_list.all_added', itemNameTr)"
              :items="missing"
              :hint="autoCompleteHint"
              persistent-hint
            >
              <template #selection="{ item }">
                <prioritized-list-entry :data="itemData(item)" />
              </template>
              <template #item="{ item }">
                <prioritized-list-entry :data="itemData(item)" />
              </template>
            </v-autocomplete>
          </v-col>
          <v-col cols="auto">
            <v-tooltip open-delay="400" top>
              <template #activator="{ on, attrs }">
                <v-btn
                  id="add-item-btn"
                  color="primary"
                  v-bind="attrs"
                  icon
                  class="mt-3"
                  :disabled="!selection"
                  v-on="on"
                  @click="addItem()"
                >
                  <v-icon>mdi-plus</v-icon>
                </v-btn>
              </template>
              <span>
                {{ t('prioritized_list.add_tooltip', itemNameTr) }}
              </span>
            </v-tooltip>
          </v-col>
        </v-row>
      </div>
      <v-simple-table>
        <thead>
          <tr>
            <th class="prioritized-list-selection__move" />
            <th class="prioritized-list-selection__priority text-center">
              {{ t('common.priority') }}
            </th>
            <th class="ps-6">{{ t('common.name') }}</th>
            <th />
          </tr>
        </thead>
        <tbody>
          <tr v-if="noResults">
            <td colspan="4">
              <v-row class="pa-3 text-h6" justify="center">
                <v-col cols="auto">
                  {{ t('prioritized_list.item.empty', itemNameTr) }}
                </v-col>
              </v-row>
            </td>
          </tr>
          <tr v-for="(identifier, index) in value" :key="identifier">
            <td>
              <div class="flex flex-column py-2">
                <div>
                  <v-btn
                    :id="'move-up-' + identifier"
                    icon
                    small
                    :disabled="isFirst(identifier)"
                    @click="move(identifier, false)"
                  >
                    <v-icon>mdi-chevron-up</v-icon>
                  </v-btn>
                </div>
                <div>
                  <v-btn
                    :id="'move-down-' + identifier"
                    icon
                    small
                    :disabled="isLast(identifier)"
                    @click="move(identifier, true)"
                  >
                    <v-icon>mdi-chevron-down</v-icon>
                  </v-btn>
                </div>
              </div>
            </td>
            <td class="text-center">{{ index + 1 }}</td>
            <td>
              <prioritized-list-entry :data="itemData(identifier)" />
            </td>
            <td class="text-end">
              <v-tooltip v-if="!disableDelete" open-delay="400" top>
                <template #activator="{ on, attrs }">
                  <v-btn
                    :id="'delete-' + identifier"
                    icon
                    v-bind="attrs"
                    v-on="on"
                    @click="remove(identifier)"
                  >
                    <v-icon>mdi-close</v-icon>
                  </v-btn>
                </template>
                <span>
                  {{ t('prioritized_list.item.delete', itemNameTr) }}
                </span>
              </v-tooltip>
            </td>
          </tr>
        </tbody>
      </v-simple-table>
    </v-sheet>
    <action-status-indicator class="mt-4" :status="status" />
  </div>
</template>

<style scoped lang="scss">
.prioritized-list-selection {
  &__move {
    width: 48px;
  }

  &__priority {
    width: 60px;
  }
}
</style>

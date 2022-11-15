<template>
  <div>
    <v-sheet outlined rounded class="mt-4">
      <div class="pb-0" :class="slots.title ? 'pa-4' : 'pa-0'">
        <div v-if="slots.title" class="text-h5 pt-2 pb-4">
          <slot name="title" />
        </div>

        <v-row v-if="!disableAdd" class="mb-4" no-gutters align="center">
          <v-col class="pr-4">
            <v-autocomplete
              v-model="selection"
              prepend-inner-icon="mdi-magnify"
              outlined
              :no-data-text="tc('prioritized_list.all_added', 0, itemNameTr)"
              :items="missing"
              hide-details
            >
              <template #selection="{ item }">
                <prioritized-list-entry :data="item" />
              </template>
              <template #item="{ item }">
                <prioritized-list-entry :data="item" />
              </template>
            </v-autocomplete>
          </v-col>
          <v-col cols="auto">
            <v-tooltip open-delay="400" top>
              <template #activator="{ on, attrs }">
                <v-btn
                  color="primary"
                  v-bind="attrs"
                  icon
                  :disabled="!selection"
                  v-on="on"
                  @click="addItem"
                >
                  <v-icon>mdi-plus</v-icon>
                </v-btn>
              </template>
              <span>
                {{ tc('prioritized_list.add_tooltip', 0, itemNameTr) }}
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
                  {{ tc('prioritized_list.item.empty', 0, itemNameTr) }}
                </v-col>
              </v-row>
            </td>
          </tr>
          <tr v-for="(identifier, index) in value" :key="identifier">
            <td>
              <div class="flex flex-column pt-3 pb-3">
                <div>
                  <v-btn
                    icon
                    :disabled="isFirst(identifier)"
                    @click="move(identifier, false)"
                  >
                    <v-icon>mdi-chevron-up</v-icon>
                  </v-btn>
                </div>
                <div>
                  <v-btn
                    icon
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
                    icon
                    v-bind="attrs"
                    v-on="on"
                    @click="remove(identifier)"
                  >
                    <v-icon>mdi-delete-outline</v-icon>
                  </v-btn>
                </template>
                <span>
                  {{ tc('prioritized_list.item.delete', 0, itemNameTr) }}
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

<script setup lang="ts">
import { PropType } from 'vue';
import ActionStatusIndicator from '@/components/error/ActionStatusIndicator.vue';
import PrioritizedListEntry from '@/components/helper/PrioritizedListEntry.vue';
import { Nullable } from '@/types';
import { BaseMessage } from '@/types/messages';
import {
  PrioritizedListData,
  PrioritizedListItemData
} from '@/types/prioritized-list-data';
import { PrioritizedListId, EmptyListId } from '@/types/prioritized-list-id';
import { assert } from '@/utils/assertions';
import { pluralize } from '@/utils/text';

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
    name: name,
    namePluralized: pluralize(name, 2)
  };
});

const missing = computed<string[]>(() => {
  return get(allItems).itemIdsNotIn(get(value));
});

const noResults = computed<boolean>(() => {
  return get(value).length === 0;
});

const isFirst = (item: string): boolean => {
  return get(value)[0] === item;
};

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
const { tc } = useI18n();
</script>

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

<template>
  <div>
    <v-simple-table>
      <thead>
        <tr>
          <th class="address-name-priority-selection__move" />
          <th class="address-name-priority-selection__priority text-center">
            {{ t('common.priority') }}
          </th>
          <th class="ps-6">{{ t('common.name') }}</th>
        </tr>
      </thead>
      <tbody>
        <tr v-if="noResults">
          <td colspan="3">
            <v-row class="pa-3 text-h6" justify="center">
              <v-col cols="auto">
                {{ t('address_name_priority_selection.item.empty') }}
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
            <address-name-priority-entry :identifier="identifier" />
          </td>
        </tr>
      </tbody>
    </v-simple-table>
  </div>
</template>

<script setup lang="ts">
import { get } from '@vueuse/core';
import { computed, PropType, toRefs } from 'vue';
import { useI18n } from 'vue-i18n-composable';
import { BaseMessage } from '@/types/messages';
import AddressNamePriorityEntry from './AddressNamePriorityEntry.vue';

const props = defineProps({
  value: { required: true, type: Array as PropType<string[]> },
  status: {
    required: false,
    type: Object as PropType<BaseMessage>,
    default: () => null
  }
});
const emit = defineEmits(['input']);
const { value } = toRefs(props);

const input = (items: string[]) => emit('input', items);

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

const move = (item: string, down: boolean) => {
  const items = [...get(value)];
  const itemIndex = items.indexOf(item);
  const nextIndex = itemIndex + (down ? 1 : -1);
  const nextItem = items[nextIndex];
  items[nextIndex] = item;
  items[itemIndex] = nextItem;
  input(items);
};

const { t } = useI18n();
</script>

<style scoped lang="scss">
.address-name-priority-selection {
  &__move {
    width: 48px;
  }

  &__priority {
    width: 60px;
  }
}
</style>

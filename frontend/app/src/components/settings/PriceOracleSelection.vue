<template>
  <v-sheet outlined rounded class="mt-4">
    <div class="pa-4 pb-0">
      <div class="text-h5 pt-2 pb-4">
        <slot name="title" />
      </div>

      <v-row class="mb-4" no-gutters align="center">
        <v-col class="pr-4">
          <v-autocomplete
            v-model="selection"
            prepend-inner-icon="mdi-magnify"
            outlined
            :no-data-text="$t('price_oracle_selection.all_added')"
            :items="missing"
            hide-details
          >
            <template #selection="{ item }">
              <oracle-entry :identifier="item" />
            </template>
            <template #item="{ item }">
              <oracle-entry :identifier="item" />
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
            <span>{{ $t('price_oracle_selection.add_tooltip') }}</span>
          </v-tooltip>
        </v-col>
      </v-row>

      <action-status-indicator :status="status" />
    </div>

    <v-simple-table>
      <thead>
        <tr>
          <th class="price-oracle-selection__move" />
          <th class="price-oracle-selection__priority text-center">
            {{ $t('price_oracle_selection.header.priority') }}
          </th>
          <th class="ps-6">{{ $t('price_oracle_selection.header.name') }}</th>
          <th />
        </tr>
      </thead>
      <tbody>
        <tr v-if="noResults">
          <td colspan="4">
            <v-row class="pa-3 text-h6" justify="center">
              <v-col cols="auto">
                {{ $t('price_oracle_selection.item.empty') }}
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
            <oracle-entry :identifier="identifier" />
          </td>
          <td class="text-end">
            <v-tooltip open-delay="400" top>
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
              <span>{{ $t('price_oracle_selection.item.delete') }}</span>
            </v-tooltip>
          </td>
        </tr>
      </tbody>
    </v-simple-table>
  </v-sheet>
</template>
<script lang="ts">
import {
  computed,
  defineComponent,
  PropType,
  ref,
  toRefs
} from '@vue/composition-api';
import { get, set } from '@vueuse/core';
import ActionStatusIndicator from '@/components/error/ActionStatusIndicator.vue';
import OracleEntry from '@/components/settings/OracleEntry.vue';
import { ActionStatus } from '@/store/types';
import { Nullable } from '@/types';
import { assert } from '@/utils/assertions';

export default defineComponent({
  name: 'PriceOracleSelection',
  components: { OracleEntry, ActionStatusIndicator },
  props: {
    value: { required: true, type: Array as PropType<string[]> },
    allItems: { required: true, type: Array as PropType<string[]> },
    status: {
      required: false,
      type: Object as PropType<ActionStatus>,
      default: () => null
    }
  },
  emits: ['input'],
  setup(props, { emit }) {
    const { value, allItems } = toRefs(props);
    const selection = ref<Nullable<string>>(null);

    const input = (items: string[]) => emit('input', items);

    const missing = computed<string[]>(() => {
      return get(allItems).filter(item => !get(value).includes(item));
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

    const addItem = () => {
      assert(get(selection));
      const items = [...get(value)];
      items.push(get(selection)!);
      input(items);
      set(selection, null);
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

    const remove = (item: string) => {
      const items = [...get(value)];
      const itemIndex = items.indexOf(item);
      items.splice(itemIndex, 1);
      input(items);
    };

    return {
      selection,
      missing,
      noResults,
      isFirst,
      isLast,
      addItem,
      move,
      remove
    };
  }
});
</script>

<style scoped lang="scss">
.price-oracle-selection {
  &__move {
    width: 48px;
  }

  &__priority {
    width: 60px;
  }
}
</style>

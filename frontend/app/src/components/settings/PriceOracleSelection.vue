<template>
  <v-sheet outlined rounded class="mt-4">
    <v-row class="mt-2">
      <v-col class="text-h5 ms-4 mb-2">
        <slot name="title" />
      </v-col>
    </v-row>
    <v-row no-gutters align="center">
      <v-col>
        <v-autocomplete
          v-model="selection"
          prepend-inner-icon="mdi-magnify"
          outlined
          :no-data-text="$t('price_oracle_selection.all_added')"
          :items="missing"
          class="pa-3"
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
            <div class="pb-6 pe-3">
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
            </div>
          </template>
          <span>{{ $t('price_oracle_selection.add_tooltip') }}</span>
        </v-tooltip>
      </v-col>
    </v-row>

    <action-status-indicator :status="status" />

    <v-simple-table>
      <thead>
        <tr>
          <th class="price-oracle-selection__move" />
          <th class="price-oracle-selection__priority">
            {{ $t('price_oracle_selection.header.priority') }}
          </th>
          <th>{{ $t('price_oracle_selection.header.name') }}</th>
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
          <td>{{ index + 1 }}</td>
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
import { Component, Emit, Prop, Vue } from 'vue-property-decorator';
import ActionStatusIndicator from '@/components/error/ActionStatusIndicator.vue';
import OracleEntry from '@/components/settings/OracleEntry.vue';
import { ActionStatus } from '@/store/types';
import { assert } from '@/utils/assertions';

@Component({
  components: { OracleEntry, ActionStatusIndicator }
})
export default class PriceOracleSelection extends Vue {
  @Prop({ required: true, type: Array })
  value!: string[];

  @Prop({ required: true, type: Array })
  allItems!: string[];

  @Prop({ required: false, default: () => null })
  status!: ActionStatus | null;

  selection: string | null = null;

  get missing(): string[] {
    return this.allItems.filter(item => !this.value.includes(item));
  }

  @Emit()
  input(_items: string[]) {}

  get noResults(): boolean {
    return this.value.length === 0;
  }

  isFirst(oracle: string): boolean {
    return this.value[0] === oracle;
  }

  isLast(item: string): boolean {
    const items = this.value;
    return items[items.length - 1] === item;
  }

  addItem() {
    assert(this.selection);
    const items = [...this.value];
    items.push(this.selection);
    this.input(items);
    this.selection = null;
  }

  move(item: string, down: boolean) {
    const items = [...this.value];
    const itemIndex = items.indexOf(item);
    const nextIndex = itemIndex + (down ? 1 : -1);
    const nextItem = items[nextIndex];
    items[nextIndex] = item;
    items[itemIndex] = nextItem;
    this.input(items);
  }

  remove(item: string) {
    const items = [...this.value];
    const itemIndex = items.indexOf(item);
    items.splice(itemIndex, 1);
    this.input(items);
  }
}
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

<template>
  <div :class="$style.container">
    <div>
      <v-tooltip open-delay="400" top>
        <template #activator="{ on, attrs }">
          <v-btn
            icon
            v-bind="attrs"
            color="primary"
            @click="updateSortDesc"
            v-on="on"
          >
            <v-icon v-if="sortDesc">mdi-sort-descending</v-icon>
            <v-icon v-else>mdi-sort-ascending</v-icon>
          </v-btn>
        </template>
        <span v-if="sortDesc">
          {{ $t('sorting_selector.desc.sort_asc_tooltip') }}
        </span>
        <span v-else>{{ $t('sorting_selector.desc.sort_desc_tooltip') }}</span>
      </v-tooltip>
    </div>
    <div
      :class="{
        [$style.selector]: true,
        [$style.light]: !dark,
        [$style.dark]: dark
      }"
    >
      <v-select
        :value="sortBy"
        hide-details
        single-line
        dense
        outlined
        :items="sortProperties"
        @input="updateSortBy"
      />
    </div>
  </div>
</template>

<script lang="ts">
import { defineComponent, PropType, toRefs } from '@vue/composition-api';
import { setupThemeCheck } from '@/composables/common';

export default defineComponent({
  name: 'SortingSelector',
  props: {
    sortBy: {
      required: true,
      type: String
    },
    sortDesc: {
      required: true,
      type: Boolean
    },
    sortProperties: {
      required: true,
      type: Array as PropType<{ text: string; value: string }[]>
    }
  },
  emits: ['update:sort-by', 'update:sort-desc'],
  setup(props, { emit }) {
    const { sortDesc } = toRefs(props);
    const updateSortBy = (value: string) => {
      emit('update:sort-by', value);
    };
    const updateSortDesc = () => {
      emit('update:sort-desc', !sortDesc.value);
    };
    const { dark } = setupThemeCheck();
    return {
      dark,
      updateSortBy,
      updateSortDesc
    };
  }
});
</script>

<style module lang="scss">
.container {
  display: flex;
  flex-direction: row;
}

.selector {
  margin-left: 8px;
  width: 200px;
}

.dark {
  background-color: var(--v-dark-base);
}

.light {
  background-color: white;
}
</style>

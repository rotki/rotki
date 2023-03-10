<script setup lang="ts">
import { type PropType } from 'vue';
import { type IgnoredAssetsHandlingType } from '@/types/asset';
import { type NonFungibleBalance } from '@/types/nfbalances';

defineProps({
  selected: {
    required: true,
    type: Array as PropType<NonFungibleBalance[]>
  },
  ignoredAssetsHandling: {
    required: true,
    type: String as PropType<IgnoredAssetsHandlingType>
  }
});

const emit = defineEmits<{
  (e: 'update:selected', selected: NonFungibleBalance[]): void;
  (
    e: 'update:ignored-assets-handling',
    ignoredAssetsHandling: IgnoredAssetsHandlingType
  ): void;
  (e: 'mass-ignore', ignored: boolean): void;
}>();

const updateSelected = (selected: NonFungibleBalance[]) => {
  emit('update:selected', selected);
};

const updateIgnoredAssetsHandling = (
  ignoredAssetsHandling: IgnoredAssetsHandlingType
) => {
  emit('update:ignored-assets-handling', ignoredAssetsHandling);
};

const massIgnore = (ignored: boolean) => {
  emit('mass-ignore', ignored);
};

const { tc } = useI18n();

const css = useCssModule();
</script>

<template>
  <v-row>
    <v-col cols="12" md="6">
      <ignore-buttons :disabled="selected.length === 0" @ignore="massIgnore" />
      <div v-if="selected.length > 0" class="mt-2 ms-1">
        {{ tc('asset_table.selected', 0, { count: selected.length }) }}
        <v-btn small text @click="updateSelected([])">
          {{ tc('common.actions.clear_selection') }}
        </v-btn>
      </div>
    </v-col>
    <v-col cols="12" md="6" class="pb-md-8">
      <v-menu offset-y :close-on-content-click="false">
        <template #activator="{ on }">
          <v-btn outlined text height="40px" data-cy="asset-filter" v-on="on">
            {{ tc('common.actions.filter') }}
            <v-icon class="ml-2">mdi-chevron-down</v-icon>
          </v-btn>
        </template>
        <v-list>
          <v-list-item
            :class="css['filter-heading']"
            class="font-weight-bold text-uppercase py-2"
          >
            {{ tc('asset_table.filter_by_ignored_status') }}
          </v-list-item>
          <v-list-item class="pb-2">
            <v-radio-group
              :value="ignoredAssetsHandling"
              class="mt-0"
              data-cy="asset-filter-ignored"
              hide-details
              @change="updateIgnoredAssetsHandling"
            >
              <v-radio value="none" :label="tc('asset_table.show_all')" />
              <v-radio
                value="exclude"
                :label="tc('asset_table.only_show_unignored')"
              />
              <v-radio
                value="show_only"
                :label="tc('asset_table.only_show_ignored', 2)"
              />
            </v-radio-group>
          </v-list-item>
        </v-list>
      </v-menu>
    </v-col>
  </v-row>
</template>

<style module lang="scss">
.filter-heading {
  font-size: 0.875rem;
  min-height: auto;
}
</style>

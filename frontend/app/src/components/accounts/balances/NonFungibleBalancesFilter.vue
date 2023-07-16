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

const { t } = useI18n();

const css = useCssModule();
</script>

<template>
  <VRow>
    <VCol cols="12" md="6">
      <IgnoreButtons
        :disabled="selected.length === 0"
        @ignore="massIgnore($event)"
      />
      <div v-if="selected.length > 0" class="mt-2 ms-1">
        {{ t('asset_table.selected', { count: selected.length }) }}
        <VBtn small text @click="updateSelected([])">
          {{ t('common.actions.clear_selection') }}
        </VBtn>
      </div>
    </VCol>
    <VCol cols="12" md="6" class="pb-md-8">
      <VMenu offset-y :close-on-content-click="false">
        <template #activator="{ on }">
          <VBtn outlined text height="40px" data-cy="asset-filter" v-on="on">
            {{ t('common.actions.filter') }}
            <VIcon class="ml-2">mdi-chevron-down</VIcon>
          </VBtn>
        </template>
        <VList>
          <VListItem
            :class="css['filter-heading']"
            class="font-weight-bold text-uppercase py-2"
          >
            {{ t('asset_table.filter_by_ignored_status') }}
          </VListItem>
          <VListItem class="pb-2">
            <VRadioGroup
              :value="ignoredAssetsHandling"
              class="mt-0"
              data-cy="asset-filter-ignored"
              hide-details
              @change="updateIgnoredAssetsHandling($event)"
            >
              <VRadio value="none" :label="t('asset_table.show_all')" />
              <VRadio
                value="exclude"
                :label="t('asset_table.only_show_unignored')"
              />
              <VRadio
                value="show_only"
                :label="t('asset_table.only_show_ignored', 2)"
              />
            </VRadioGroup>
          </VListItem>
        </VList>
      </VMenu>
    </VCol>
  </VRow>
</template>

<style module lang="scss">
.filter-heading {
  font-size: 0.875rem;
  min-height: auto;
}
</style>

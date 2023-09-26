<script setup lang="ts">
import { type IgnoredAssetsHandlingType } from '@/types/asset';
import { type NonFungibleBalance } from '@/types/nfbalances';

defineProps<{
  selected: NonFungibleBalance[];
  ignoredAssetsHandling: IgnoredAssetsHandlingType;
}>();

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
  <div class="flex flex-row items-center justify-between flex-wrap gap-2">
    <div class="flex flex-row gap-2">
      <IgnoreButtons
        :disabled="selected.length === 0"
        @ignore="massIgnore($event)"
      />
      <div v-if="selected.length > 0" class="flex flex-row items-center gap-2">
        <span class="text-body-2 text-rui-text-secondary">{{
          t('asset_table.selected', { count: selected.length })
        }}</span>
        <RuiButton size="sm" variant="outlined" @click="updateSelected([])">
          {{ t('common.actions.clear_selection') }}
        </RuiButton>
      </div>
    </div>
    <div>
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
            class="font-bold text-uppercase py-2"
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
    </div>
  </div>
</template>

<style module lang="scss">
.filter-heading {
  font-size: 0.875rem;
  min-height: auto;
}
</style>

<script setup lang="ts">
import IgnoreButtons from '@/components/history/IgnoreButtons.vue';
import { IgnoredAssetHandlingType, type IgnoredAssetsHandlingType } from '@/types/asset';

const props = defineProps<{
  selected: string[];
  ignoredAssetsHandling: IgnoredAssetsHandlingType;
}>();

const emit = defineEmits<{
  (e: 'update:selected', selected: string[]): void;
  (e: 'update:ignored-assets-handling', ignoredAssetsHandling: IgnoredAssetsHandlingType): void;
  (e: 'mass-ignore', ignored: boolean): void;
}>();

const internalValue = computed({
  get() {
    return props.ignoredAssetsHandling;
  },
  set(value: IgnoredAssetsHandlingType) {
    emit('update:ignored-assets-handling', value);
  },
});

const disabledIgnoreActions = computed(() => {
  const ignoredAssetsHandling = get(internalValue);
  return {
    ignore: ignoredAssetsHandling === IgnoredAssetHandlingType.SHOW_ONLY,
    unIgnore: ignoredAssetsHandling === IgnoredAssetHandlingType.EXCLUDE,
  };
});

function massIgnore(ignored: boolean) {
  emit('mass-ignore', ignored);
}

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <div class="flex flex-row items-center justify-between flex-wrap gap-2">
    <div class="flex flex-row gap-2">
      <IgnoreButtons
        :disabled="selected.length === 0"
        :disabled-actions="disabledIgnoreActions"
        @ignore="massIgnore($event)"
      />
      <div
        v-if="selected.length > 0"
        class="flex flex-row items-center gap-2"
      >
        <span class="text-body-2 text-rui-text-secondary">
          {{ t('asset_table.selected', { count: selected.length }) }}
        </span>
        <RuiButton
          size="sm"
          variant="outlined"
          @click="emit('update:selected', [])"
        >
          {{ t('common.actions.clear_selection') }}
        </RuiButton>
      </div>
    </div>
    <div>
      <RuiMenu :popper="{ placement: 'bottom-end' }">
        <template #activator="{ attrs }">
          <RuiButton
            variant="outlined"
            v-bind="attrs"
          >
            <template #append>
              <RuiIcon name="lu-chevron-down" />
            </template>
            {{ t('common.actions.filter') }}
          </RuiButton>
        </template>
        <div class="p-2">
          <div class="font-bold uppercase p-2 text-sm">
            {{ t('asset_table.filter_by_ignored_status') }}
          </div>
          <div class="pb-2 px-3">
            <RuiRadioGroup
              v-model="internalValue"
              class="mt-0"
              data-cy="asset-filter-ignored"
              hide-details
              color="primary"
            >
              <RuiRadio
                value="none"
                :label="t('asset_table.show_all')"
              />
              <RuiRadio
                value="exclude"
                :label="t('asset_table.only_show_unignored')"
              />
              <RuiRadio
                value="show_only"
                :label="t('asset_table.only_show_ignored', 2)"
              />
            </RuiRadioGroup>
          </div>
        </div>
      </RuiMenu>
    </div>
  </div>
</template>

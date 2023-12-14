<script setup lang="ts">
import {
  IgnoredAssetHandlingType,
  type IgnoredAssetsHandlingType
} from '@/types/asset';

type Model = {
  onlyShowOwned: boolean;
  ignoredAssetsHandling: IgnoredAssetsHandlingType;
};

const props = defineProps<{
  value: Model;
  count: number;
}>();

const emit = defineEmits<{
  (e: 'input', value: Model): void;
}>();

const { t } = useI18n();
const css = useCssModule();

const showMenu = ref(false);

const isHandlingType = (t: any): t is IgnoredAssetsHandlingType =>
  Object.values(IgnoredAssetHandlingType).includes(t);

const handlingSelection = computed({
  get() {
    return props.value.ignoredAssetsHandling;
  },
  set(value: string) {
    if (isHandlingType(value)) {
      emit('input', {
        ...props.value,
        ignoredAssetsHandling: value
      });
    }
  }
});

const onlyShowOwned = computed({
  get() {
    return props.value.onlyShowOwned;
  },
  set(value: boolean) {
    emit('input', {
      ...props.value,
      onlyShowOwned: value
    });
  }
});
</script>

<template>
  <VMenu v-model="showMenu" offset-y :close-on-content-click="false">
    <template #activator="{ on }">
      <RuiButton
        variant="outlined"
        data-cy="asset-filter"
        color="secondary"
        v-on="on"
      >
        <template #append>
          <RuiIcon name="arrow-down-s-line" />
        </template>
        {{ t('common.actions.filter') }}
      </RuiButton>
    </template>
    <VList data-cy="asset-filter-menu">
      <RuiCheckbox
        v-model="onlyShowOwned"
        data-cy="asset-filter-only-show-owned"
        class="mt-0 px-4 py-2"
        :label="t('asset_table.only_show_owned')"
        hide-details
      />
      <VListItem
        :class="css['filter-heading']"
        class="font-bold text-uppercase py-2"
      >
        {{ t('asset_table.filter_by_ignored_status') }}
      </VListItem>
      <VListItem>
        <RuiRadioGroup
          v-if="showMenu"
          v-model="handlingSelection"
          color="primary"
          class="mt-0"
          data-cy="asset-filter-ignored"
        >
          <RuiRadio
            internal-value="none"
            data-cy="asset-filter-none"
            :label="t('asset_table.show_all')"
          />
          <RuiRadio
            internal-value="exclude"
            data-cy="asset-filter-exclude"
            :label="t('asset_table.only_show_unignored')"
          />
          <RuiRadio
            internal-value="show_only"
            data-cy="asset-filter-show_only"
            :label="
              t(
                'asset_table.only_show_ignored',
                {
                  length: count
                },
                1
              )
            "
          />
        </RuiRadioGroup>
      </VListItem>
    </VList>
  </VMenu>
</template>

<style module lang="scss">
.filter-heading {
  font-size: 0.875rem;
  min-height: auto;
}
</style>

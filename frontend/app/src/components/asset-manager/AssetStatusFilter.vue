<script setup lang="ts">
import TableStatusFilter from '@/components/helper/TableStatusFilter.vue';
import { IgnoredAssetHandlingType, type IgnoredAssetsHandlingType } from '@/types/asset';
import { useRefPropVModel } from '@/utils/model';

interface Model {
  onlyShowOwned: boolean;
  onlyShowWhitelisted: boolean;
  ignoredAssetsHandling: IgnoredAssetsHandlingType;
}

const modelValue = defineModel<Model>({ required: true });

defineProps<{
  count: number;
}>();

const emit = defineEmits<{
  'refresh:ignored': [];
}>();

const { t } = useI18n({ useScope: 'global' });
const showMenu = ref<boolean>(false);

const handlingSelection = useRefPropVModel(modelValue, 'ignoredAssetsHandling');
const onlyShowOwned = useRefPropVModel(modelValue, 'onlyShowOwned');
const onlyShowWhitelisted = useRefPropVModel(modelValue, 'onlyShowWhitelisted');

watch(handlingSelection, (value) => {
  if (value === IgnoredAssetHandlingType.SHOW_ONLY)
    emit('refresh:ignored');
});
</script>

<template>
  <TableStatusFilter v-model="showMenu">
    <div
      class="p-1 pt-2"
      data-cy="asset-filter-menu"
    >
      <RuiCheckbox
        v-model="onlyShowOwned"
        color="primary"
        data-cy="asset-filter-only-show-owned"
        class="mt-0 px-3"
        :label="t('asset_table.only_show_owned')"
        hide-details
      />
      <RuiCheckbox
        v-model="onlyShowWhitelisted"
        color="primary"
        data-cy="asset-filter-only-show-whitelisted"
        class="mt-0 px-3"
        :label="t('asset_table.only_show_whitelisted')"
        hide-details
      />
      <div class="font-bold uppercase p-2 text-sm">
        {{ t('asset_table.filter_by_ignored_status') }}
      </div>
      <div class="pb-2 px-3">
        <RuiRadioGroup
          v-if="showMenu"
          v-model="handlingSelection"
          color="primary"
          class="mt-0"
          hide-details
          data-cy="asset-filter-ignored"
        >
          <RuiRadio
            value="none"
            data-cy="asset-filter-none"
            :label="t('asset_table.show_all')"
          />
          <RuiRadio
            value="exclude"
            data-cy="asset-filter-exclude"
            :label="t('asset_table.only_show_unignored')"
          />
          <RuiRadio
            value="show_only"
            data-cy="asset-filter-show_only"
            :label="
              t(
                'asset_table.only_show_ignored',
                {
                  length: count,
                },
                1,
              )
            "
          />
        </RuiRadioGroup>
      </div>
    </div>
  </TableStatusFilter>
</template>

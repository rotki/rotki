<script setup lang="ts">
import AssetManagerMoreTitle from '@/modules/assets/admin/AssetManagerMoreTitle.vue';
import TablePageLayout from '@/modules/shell/layout/TablePageLayout.vue';

/** The page frame of an asset mapping admin (exchange or counterparty): title, Refresh and Add. */
const { loading, addTestId } = defineProps<{
  loading: boolean;
  addTestId: string;
}>();

const emit = defineEmits<{
  refresh: [];
  add: [];
}>();

defineSlots<{
  default: () => any;
}>();

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <TablePageLayout child>
    <template #title>
      <AssetManagerMoreTitle />
    </template>
    <template #buttons>
      <RuiButton
        color="primary"
        variant="outlined"
        :loading="loading"
        @click="emit('refresh')"
      >
        <template #prepend>
          <RuiIcon name="lu-refresh-ccw" />
        </template>
        {{ t('common.refresh') }}
      </RuiButton>

      <RuiButton
        :data-testid="addTestId"
        color="primary"
        @click="emit('add')"
      >
        <template #prepend>
          <RuiIcon name="lu-plus" />
        </template>
        {{ t('asset_management.cex_mapping.add_mapping') }}
      </RuiButton>
    </template>
    <slot />
  </TablePageLayout>
</template>

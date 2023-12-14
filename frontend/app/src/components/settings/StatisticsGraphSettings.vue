<script setup lang="ts">
const emit = defineEmits<{
  (e: 'updated'): void;
}>();

const { t } = useI18n();

const updated = () => emit('updated');

const showMenu: Ref<boolean> = ref(false);
</script>

<template>
  <VMenu
    v-model="showMenu"
    max-width="500px"
    min-width="280px"
    left
    :close-on-content-click="false"
  >
    <template #activator="{ on }">
      <MenuTooltipButton
        :tooltip="t('statistics_graph_settings.tooltip')"
        class-name="graph-period"
        :on-menu="on"
      >
        <RuiIcon name="settings-4-line" />
      </MenuTooltipButton>
    </template>

    <RuiCard variant="flat">
      <SsfGraphMultiplierSetting @updated="updated()" />
      <RuiDivider class="my-4" />
      <InferZeroTimedBalancesSetting @updated="updated()" />

      <template #footer>
        <div class="grow" />
        <RuiButton color="primary" @click="showMenu = false">
          {{ t('common.actions.close') }}
        </RuiButton>
      </template>
    </RuiCard>
  </VMenu>
</template>

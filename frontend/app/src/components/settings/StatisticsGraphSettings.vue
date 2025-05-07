<script setup lang="ts">
import MenuTooltipButton from '@/components/helper/MenuTooltipButton.vue';
import InferZeroTimedBalancesSetting from '@/components/settings/InferZeroTimedBalancesSetting.vue';
import SsfGraphMultiplierSetting from '@/components/settings/SsfGraphMultiplierSetting.vue';

const emit = defineEmits<{
  (e: 'updated'): void;
}>();

const { t } = useI18n({ useScope: 'global' });

const updated = () => emit('updated');

const showMenu = ref<boolean>(false);
</script>

<template>
  <RuiMenu
    v-model="showMenu"
    menu-class="min-w-[18rem] max-w-[20rem]"
    :popper="{ placement: 'bottom-end' }"
  >
    <template #activator="{ attrs }">
      <MenuTooltipButton
        :tooltip="t('statistics_graph_settings.tooltip')"
        class-name="graph-period"
        custom-color
        v-bind="attrs"
      >
        <RuiIcon name="lu-settings" />
      </MenuTooltipButton>
    </template>

    <div class="p-4 overflow-y-auto">
      <SsfGraphMultiplierSetting @updated="updated()" />
      <RuiDivider class="my-4" />
      <InferZeroTimedBalancesSetting @updated="updated()" />

      <div class="flex justify-end">
        <RuiButton
          color="primary"
          @click="showMenu = false"
        >
          {{ t('common.actions.close') }}
        </RuiButton>
      </div>
    </div>
  </RuiMenu>
</template>

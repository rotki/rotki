<script setup lang="ts">
import AskUserUponSizeDiscrepancySetting from '@/components/settings/general/AskUserUponSizeDiscrepancySetting.vue';

const model = defineModel<boolean>({ required: true });

const { t } = useI18n({ useScope: 'global' });
const { isMdAndUp } = useBreakpoint();
</script>

<template>
  <RuiMenu
    v-model="model"
    :popper="{ placement: isMdAndUp ? 'right-start' : 'bottom-end' }"
    :close-on-content-click="false"
  >
    <template #activator="{ attrs }">
      <RuiButton
        variant="text"
        icon
        size="sm"
        class="!p-2"
        v-bind="attrs"
      >
        <RuiIcon
          size="20"
          name="lu-settings"
        />
      </RuiButton>
    </template>
    <div class="p-4 w-[18rem] max-w-[calc(100vw-1rem)]">
      <div>
        <div class="text-body-1 font-medium mb-3">
          {{ t('sync_indicator.setting.title') }}
        </div>
        <AskUserUponSizeDiscrepancySetting dialog />
      </div>

      <div class="flex justify-end">
        <RuiButton
          color="primary"
          variant="outlined"
          @click="model = false"
        >
          {{ t('common.actions.close') }}
        </RuiButton>
      </div>
    </div>
  </RuiMenu>
</template>

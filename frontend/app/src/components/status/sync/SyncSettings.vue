<script setup lang="ts">
import { useBreakpoint } from '@rotki/ui-library-compat';

const props = defineProps<{
  value: boolean;
}>();

const emit = defineEmits<{
  (e: 'input', value: boolean): void;
}>();

const vModel = useSimpleVModel(props, emit);
const { t } = useI18n();
const { isMdAndUp } = useBreakpoint();
</script>

<template>
  <RuiMenu
    v-model="vModel"
    :popper="{ placement: isMdAndUp ? 'right-start' : 'bottom-end' }"
    :close-on-content-click="false"
  >
    <template #activator="{ on }">
      <RuiButton
        variant="text"
        icon
        size="sm"
        class="!p-2"
        v-on="on"
      >
        <RuiIcon
          size="20"
          name="settings-4-line"
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
          @click="vModel = false"
        >
          {{ t('common.actions.close') }}
        </RuiButton>
      </div>
    </div>
  </RuiMenu>
</template>

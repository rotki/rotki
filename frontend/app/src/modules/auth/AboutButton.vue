<script setup lang="ts">
import { set } from '@vueuse/shared';
import { storeToRefs } from 'pinia';
import { useI18n } from 'vue-i18n';
import { useAreaVisibilityStore } from '@/modules/core/common/use-area-visibility-store';

const { t } = useI18n({ useScope: 'global' });
const { showAbout } = storeToRefs(useAreaVisibilityStore());

function show() {
  set(showAbout, true);
}
</script>

<template>
  <RuiTooltip
    :text="t('account_management.about_tooltip')"
    :options="{ offset: 0, placement: 'top' }"
  >
    <template #activator>
      <RuiButton
        variant="text"
        color="primary"
        icon
        rounded
        @click="show()"
      >
        <RuiIcon name="lu-info" />
      </RuiButton>
    </template>
  </RuiTooltip>
</template>

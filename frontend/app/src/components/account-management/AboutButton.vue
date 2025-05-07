<script setup lang="ts">
import { useAreaVisibilityStore } from '@/store/session/visibility';

const { t } = useI18n({ useScope: 'global' });
const { showAbout } = storeToRefs(useAreaVisibilityStore());

function show() {
  set(showAbout, true);
}
</script>

<template>
  <RuiTooltip
    :text="t('account_management.about_tooltip')"
    :popper="{ placement: 'top', offsetDistance: 0 }"
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

<script setup lang="ts">
const { t } = useI18n();
const { showAbout } = storeToRefs(useAreaVisibilityStore());

const show = () => {
  set(showAbout, true);
};
</script>

<template>
  <RuiTooltip
    :text="t('account_management.about_tooltip')"
    :popper="{ placement: 'top', offsetDistance: 0 }"
  >
    <template #activator>
      <RuiButton variant="text" color="primary" icon rounded @click="show()">
        <RuiIcon name="information-line" />
      </RuiButton>
    </template>
  </RuiTooltip>
</template>

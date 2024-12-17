<script setup lang="ts">
import { usePremium } from '@/composables/premium';
import WrappedDialog from './WrappedDialog.vue';

const dialog = ref(false);
const premium = usePremium();
const { t } = useI18n();
const { isLgAndDown } = useBreakpoint();
const tooltipText = computed(() =>
  premium.value ? t('wrapped.tooltip') : t('wrapped.premium_required_tooltip'),
);

function showDialog() {
  if (get(premium)) {
    dialog.value = true;
  }
}

function onClose() {
  dialog.value = false;
}
</script>

<template>
  <div>
    <RuiTooltip
      :popper="{ placement: 'bottom' }"
    >
      <template #activator>
        <RuiButton
          :icon="false"
          color="primary"
          variant="outlined"
          :rounded="false"
          :elevation="null"
          data-cy="year-wrapped-button"
          class="lg:!py-2"
          @click="showDialog()"
        >
          <template #prepend>
            <RuiIcon name="gift-2-line" />
          </template>
          <span v-if="!isLgAndDown">{{ t('wrapped.title') }}</span>
        </RuiButton>
      </template>
      <span>{{ tooltipText }}</span>
    </RuiTooltip>
    <WrappedDialog
      v-if="premium"
      v-model:display="dialog"
      @close="onClose()"
    />
  </div>
</template>

<script setup lang="ts">
import WrappedDialog from '@/components/wrapped/WrappedDialog.vue';

const dialog = ref(false);
const { t } = useI18n();
const currentYear = computed(() => new Date().getFullYear());

function showDialog() {
  set(dialog, true);
}

function onClose() {
  set(dialog, false);
}
</script>

<template>
  <div class="mr-2">
    <RuiTooltip
      :popper="{ placement: 'bottom' }"
      :open-delay="400"
    >
      <template #activator>
        <RuiButton
          color="primary"
          variant="outlined"
          data-cy="year-wrapped-button"
          class="lg:!py-2 [&_span]:!hidden lg:[&_span]:!block"
          @click="showDialog()"
        >
          <template #prepend>
            <RuiIcon name="gift-2-line" />
          </template>
          {{ t('wrapped.title') }}
        </RuiButton>
      </template>
      {{ t('wrapped.tooltip', { year: get(currentYear) }) }}
    </RuiTooltip>
    <WrappedDialog
      v-model:display="dialog"
      @close="onClose()"
    />
  </div>
</template>

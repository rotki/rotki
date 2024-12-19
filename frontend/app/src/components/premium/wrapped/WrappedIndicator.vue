<script setup lang="ts">
import { usePremium } from '@/composables/premium.ts';
import WrappedDialog from './WrappedDialog.vue';

const dialog = ref(false);
const premium = usePremium();
const { t } = useI18n();
const currentYear = computed(() => new Date().getFullYear());
const tooltipText = computed(() =>
  get(premium) ? t('wrapped.tooltip', { year: get(currentYear) }) : t('wrapped.premium_required_tooltip'),
);

function showDialog() {
  if (get(premium)) {
    set(dialog, true);
  }
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
          v-if="premium"
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
        <RuiBadge
          v-else
          placement="top"
          offset-y="6"
          offset-x="-6"
          size="sm"
        >
          <template #icon>
            <RuiIcon
              name="lock-line"
              size="10"
            />
          </template>
          <RuiButton
            color="primary"
            variant="outlined"
            data-cy="year-wrapped-button"
            class="lg:!py-2 [&_span]:!hidden lg:[&_span]:!block"
          >
            <template #prepend>
              <RuiIcon name="gift-2-line" />
            </template>
            {{ t('wrapped.title') }}
          </RuiButton>
        </RuiBadge>
      </template>
      {{ tooltipText }}
    </RuiTooltip>
    <WrappedDialog
      v-if="premium"
      v-model:display="dialog"
      @close="onClose()"
    />
  </div>
</template>

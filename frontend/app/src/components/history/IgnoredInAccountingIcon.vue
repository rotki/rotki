<script setup lang="ts">
import BadgeDisplay from '@/components/history/BadgeDisplay.vue';

withDefaults(
  defineProps<{
    mobile?: boolean;
  }>(),
  {
    mobile: false,
  },
);

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <div>
    <BadgeDisplay
      v-if="mobile"
      color="grey"
      class="items-center gap-2"
    >
      <RuiIcon
        size="18"
        name="lu-eye-off"
      />
      {{ t('common.ignored_in_accounting') }}
    </BadgeDisplay>
    <RuiTooltip
      v-else
      :popper="{ placement: 'bottom' }"
      :open-delay="400"
    >
      <template #activator>
        <BadgeDisplay
          color="grey"
          class="py-1"
        >
          <RuiIcon
            size="18"
            name="lu-eye-off"
          />
        </BadgeDisplay>
      </template>
      {{ t('common.ignored_in_accounting') }}
    </RuiTooltip>
  </div>
</template>

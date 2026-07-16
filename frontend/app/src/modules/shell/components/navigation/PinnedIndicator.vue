<script setup lang="ts">
import MenuTooltipButton from '@/modules/shell/components/MenuTooltipButton.vue';
import { usePinnedTabs } from '@/modules/shell/pinned/use-pinned-tabs';

const visible = defineModel<boolean>('visible', { required: true });

const { tabs } = usePinnedTabs();
const { t } = useI18n({ useScope: 'global' });

const count = computed<number>(() => get(tabs).length);

function toggleVisibility(): void {
  set(visible, !get(visible));
}
</script>

<template>
  <MenuTooltipButton
    v-if="count > 0"
    :tooltip="t('pinned.tooltip')"
    data-testid="pinned-indicator"
    @click="toggleVisibility()"
  >
    <RuiBadge
      color="primary"
      :dot="count < 2"
      :text="count.toString()"
      placement="top"
      offset-y="4"
      size="lg"
      class="flex items-center"
    >
      <RuiIcon
        :class="{ '-rotate-[25deg]': visible }"
        name="lu-pin"
      />
    </RuiBadge>
  </MenuTooltipButton>
</template>

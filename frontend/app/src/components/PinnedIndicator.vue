<script setup lang="ts">
import MenuTooltipButton from '@/components/helper/MenuTooltipButton.vue';
import { useAreaVisibilityStore } from '@/store/session/visibility';

const visible = defineModel<boolean>('visible', { required: true });

const { pinned } = storeToRefs(useAreaVisibilityStore());
const { t } = useI18n({ useScope: 'global' });

function toggleVisibility(): void {
  set(visible, !get(visible));
}
</script>

<template>
  <MenuTooltipButton
    v-if="pinned"
    :tooltip="t('pinned.tooltip')"
    @click="toggleVisibility()"
  >
    <RuiBadge
      color="primary"
      dot
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

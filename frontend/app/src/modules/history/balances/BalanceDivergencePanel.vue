<script setup lang="ts">
import BalanceDivergenceView from '@/modules/history/balances/BalanceDivergenceView.vue';

const modelValue = defineModel<boolean>({ required: true });
const panelRef = useTemplateRef<HTMLElement>('panelRef');
const panelEngaged = ref<boolean>(false);

// Autocomplete menus are teleported outside the drawer. Keep the drawer stateless while a
// control is focused, and briefly after blur, so clicking a suggestion is not treated as an
// outside click that closes the panel.
const { focused: panelFocused } = useFocusWithin(panelRef);
const { start: scheduleDisengage, stop: cancelDisengage } = useTimeoutFn(() => {
  set(panelEngaged, false);
}, 300, { immediate: false });

watch(panelFocused, (focused) => {
  if (focused) {
    cancelDisengage();
    set(panelEngaged, true);
  }
  else {
    scheduleDisengage();
  }
});

function close(): void {
  set(modelValue, false);
}
</script>

<template>
  <RuiNavigationDrawer
    v-model="modelValue"
    width="450px"
    position="right"
    temporary
    :stateless="panelEngaged"
  >
    <div
      ref="panelRef"
      class="h-full"
    >
      <BalanceDivergenceView @close="close()" />
    </div>
  </RuiNavigationDrawer>
</template>

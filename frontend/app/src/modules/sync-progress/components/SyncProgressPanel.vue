<script setup lang="ts">
import { onClickOutside, onKeyStroke, useElementBounding } from '@vueuse/core';
import { useSyncProgress } from '../composables/use-sync-progress';
import { SyncPhase } from '../types';
import SyncProgressDetails from './SyncProgressDetails.vue';
import SyncProgressHeader from './SyncProgressHeader.vue';

const { isActive, phase, canDismiss } = useSyncProgress();

const expanded = ref<boolean>(false);
const dismissed = ref<boolean>(false);
const panelRef = useTemplateRef<HTMLDivElement>('panelRef');
const detailsRef = useTemplateRef<HTMLDivElement>('detailsRef');

const visible = computed<boolean>(() => get(isActive) && !get(dismissed));

const { left, bottom, width } = useElementBounding(panelRef);

const detailsStyle = computed<{ left: string; top: string; width: string }>(() => ({
  left: `${get(left)}px`,
  top: `${get(bottom)}px`,
  width: `${get(width)}px`,
}));

function toggle(): void {
  set(expanded, !get(expanded));
}

function collapse(): void {
  set(expanded, false);
}

function dismiss(): void {
  set(dismissed, true);
}

// Close on click outside (check both panel and details)
onClickOutside(
  panelRef,
  (event) => {
    const details = get(detailsRef);
    if (details && details.contains(event.target as Node))
      return;
    collapse();
  },
  { ignore: [detailsRef] },
);

// Close on Escape key
onKeyStroke('Escape', () => {
  if (get(expanded))
    collapse();
});

watch(phase, (newPhase, oldPhase) => {
  // Reset dismissed state when a new sync starts
  if (oldPhase === SyncPhase.COMPLETE && newPhase === SyncPhase.SYNCING) {
    set(dismissed, false);
  }
});
</script>

<template>
  <div>
    <Transition
      enter-from-class="opacity-0 -translate-y-2"
      enter-to-class="opacity-100 translate-y-0"
      enter-active-class="transition-all duration-200 ease-out"
      leave-from-class="opacity-100 translate-y-0"
      leave-to-class="opacity-0 -translate-y-2"
      leave-active-class="transition-all duration-150 ease-in"
    >
      <div
        v-if="visible"
        ref="panelRef"
        class="relative border"
        :class="expanded ? 'border-default z-[200]' : 'border-white dark:border-dark-elevated'"
      >
        <div class="border-b border-default bg-white dark:bg-dark-elevated">
          <SyncProgressHeader
            :expanded="expanded"
            :can-dismiss="canDismiss"
            @toggle="toggle()"
            @dismiss="dismiss()"
          />
        </div>

        <!-- Teleport details to overlay content -->
        <Teleport to="body">
          <!-- Backdrop -->
          <Transition
            enter-from-class="opacity-0"
            enter-to-class="opacity-100"
            enter-active-class="transition-opacity duration-200"
            leave-from-class="opacity-100"
            leave-to-class="opacity-0"
            leave-active-class="transition-opacity duration-150"
          >
            <div
              v-if="expanded"
              class="fixed inset-0 z-[199] bg-black/20 backdrop-blur-[1px]"
              @click="collapse()"
            />
          </Transition>

          <!-- Details dropdown -->
          <Transition
            enter-from-class="opacity-0 -translate-y-1"
            enter-to-class="opacity-100 translate-y-0"
            enter-active-class="transition-all duration-200 ease-out"
            leave-from-class="opacity-100 translate-y-0"
            leave-to-class="opacity-0 -translate-y-1"
            leave-active-class="transition-all duration-150 ease-in"
          >
            <div
              v-if="expanded"
              ref="detailsRef"
              class="fixed z-[200]"
              :style="detailsStyle"
            >
              <div class="border border-t-0 border-default rounded-b-lg bg-white dark:bg-dark-elevated shadow-xl max-h-[calc(100vh-8rem)] overflow-y-auto">
                <SyncProgressDetails />
              </div>
            </div>
          </Transition>
        </Teleport>
      </div>
    </Transition>
  </div>
</template>

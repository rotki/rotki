<script setup lang="ts">
import { PinnedNames } from '@/modules/session/types';
import { usePinnedPanel } from '@/modules/shell/pinned/use-pinned-panel';

const { t } = useI18n({ useScope: 'global' });

const { isPinned, toggle: togglePanel } = usePinnedPanel(PinnedNames.BALANCE_DIVERGENCE);

const active = isPinned;

/**
 * Opens or closes the divergence search.
 *
 * @remarks
 * The search has no overlay of its own any more, so this pins the rail panel and reveals it, or
 * closes it if it is already pinned. No payload is passed because the panel takes none.
 */
function toggle(): void {
  togglePanel({});
}
</script>

<template>
  <RuiTooltip :open-delay="300">
    <template #activator>
      <RuiButton
        variant="outlined"
        color="primary"
        size="sm"
        :class="{ '!bg-rui-primary !text-white': active }"
        data-testid="balance-divergence-toggle"
        @click="toggle()"
      >
        <RuiIcon
          name="lu-search"
          size="16"
        />
      </RuiButton>
    </template>
    {{ t('balance_divergence.action') }}
  </RuiTooltip>
</template>

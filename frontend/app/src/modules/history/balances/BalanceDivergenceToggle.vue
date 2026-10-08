<script setup lang="ts">
import { useAreaVisibilityStore } from '@/modules/core/common/use-area-visibility-store';
import { PinnedNames } from '@/modules/session/types';
import { usePinnedPanel } from '@/modules/shell/pinned/use-pinned-panel';

const { t } = useI18n({ useScope: 'global' });

const { pinnedPanels } = storeToRefs(useAreaVisibilityStore());
const { isPinned, pin, toggle: togglePanel } = usePinnedPanel(PinnedNames.BALANCE_DIVERGENCE);

const active = isPinned;

/** The panel is pinned on a data issue's search rather than on the manual search form. */
const showsIssue = computed<boolean>(() => get(pinnedPanels).some(
  panel => panel.name === PinnedNames.BALANCE_DIVERGENCE && !!panel.props.issue,
));

/**
 * Opens or closes the divergence search.
 *
 * @remarks
 * The search has no overlay of its own any more, so this pins the rail panel and reveals it, or
 * closes it if it is already pinned. A panel left on a data issue's search is switched to the
 * manual search form instead, since that form is what this button offers.
 */
function toggle(): void {
  if (get(showsIssue))
    pin({});
  else
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

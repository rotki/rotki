<script setup lang="ts">
import { type DisplayKind, DisplayKinds, type FieldDef, type ValueDisplay, type ValueIcon, type ValueSwatch } from '@/modules/core/table/pill/core/types';
import { useScramble } from '@/modules/settings/use-scramble';
import AssetIcon from '@/modules/shell/components/AssetIcon.vue';
import ChainIcon from '@/modules/shell/components/ChainIcon.vue';
import CounterpartyDisplay from '@/modules/shell/components/display/CounterpartyDisplay.vue';
import EnsAvatar from '@/modules/shell/components/display/EnsAvatar.vue';
import LocationIcon from '@/modules/shell/components/display/LocationIcon.vue';

/**
 * The icon for one filter value, chosen by the field's display kind. One mapping shared by the
 * pill and the value checklist, so a value looks the same wherever it appears. A field with no
 * display kind (a plain enum, a date, an amount) renders nothing, unless it resolved a plain
 * `icon` for the value, which wins over the display kind.
 *
 * The asset icon's own chain badge is suppressed: at this size it hangs outside its box. The
 * chain is shown separately, next to the value.
 */
const { display, value, valueDisplay, icon, swatch, size = '16px' } = defineProps<{
  display: FieldDef['display'];
  value: string;
  /**
   * This value's own display (`FieldDef.resolveDisplay`), for a field whose values are of more
   * than one kind. Overrides `display`, and may name what the icon is drawn from.
   */
  valueDisplay?: ValueDisplay;
  /** A field-resolved plain icon (`FieldDef.resolveIcon`), for values that are neither identities nor a display kind. */
  icon?: ValueIcon;
  /** A field-resolved colour pair (`FieldDef.resolveSwatch`), for a value that is itself a colour (a tag). */
  swatch?: ValueSwatch;
  size?: string;
}>();

/**
 * Privacy mode has to reach the icon too: a blockie is derived from the address bytes, so an
 * unscrambled one leaks the identity just as the text would.
 */
const { scrambleAddress } = useScramble();

// The display-kind icons take a CSS length, `RuiIcon` takes a unitless pixel count.
const iconSize = computed<number>(() => Number.parseInt(size, 10));

/** What the template draws. Several kinds share a mark: an account and a bare address both get one. */
type IconMark = 'asset' | 'avatar' | 'chain' | 'location' | 'counterparty' | 'none';

/**
 * Chosen in the script rather than by a chain of comparisons in the template, so that adding a
 * display kind is a compile error here instead of a value that quietly renders no icon at all:
 * a `switch` over the union with a declared return type has to cover every member.
 */
function markFor(kind: DisplayKind | undefined): IconMark {
  switch (kind) {
    case DisplayKinds.ASSET:
      return 'asset';
    case DisplayKinds.ACCOUNT:
    case DisplayKinds.ADDRESS:
      return 'avatar';
    case DisplayKinds.CHAIN:
      return 'chain';
    case DisplayKinds.LOCATION:
      return 'location';
    case DisplayKinds.COUNTERPARTY:
      return 'counterparty';
    case undefined:
      return 'none';
  }
}

const mark = computed<IconMark>(() => markFor(valueDisplay?.kind ?? display));

// An exchange account's icon comes from its location, not from the account name being filtered on.
const iconValue = computed<string>(() => valueDisplay?.source ?? value);
</script>

<template>
  <RuiIcon
    v-if="icon"
    :name="icon.icon"
    :color="icon.color"
    :size="iconSize"
  />
  <!-- A tag is recognised by its own two colours, so the swatch carries both: the border is the
       tag's foreground, which is what keeps a light tag visible on a light pill. -->
  <span
    v-else-if="swatch"
    class="rounded-sm border shrink-0"
    :style="{ backgroundColor: swatch.background, borderColor: swatch.foreground, height: size, width: size }"
  />
  <AssetIcon
    v-else-if="mark === 'asset'"
    :identifier="iconValue"
    :size="size"
    :show-chain="false"
  />
  <EnsAvatar
    v-else-if="mark === 'avatar'"
    :address="scrambleAddress(iconValue)"
    avatar
    :size="size"
  />
  <ChainIcon
    v-else-if="mark === 'chain'"
    :chain="iconValue"
    :size="size"
  />
  <LocationIcon
    v-else-if="mark === 'location'"
    :item="iconValue"
    icon
    :size="size"
  />
  <CounterpartyDisplay
    v-else-if="mark === 'counterparty'"
    :counterparty="iconValue"
    icon
    :size="size"
  />
</template>

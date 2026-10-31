import type { ComputedRef, MaybeRefOrGetter } from 'vue';
import type { InteractionConnection } from './address-interaction-graph';

/**
 * Categorical edge colors, in a fixed order, each stepped separately for the light and dark surface.
 *
 * @remarks
 * Validated against the chart surfaces (`#fafafa` light, `#18181b` dark). Adjacent pairs clear the
 * colour-blind and normal-vision floors in both modes. Only the first three clear them across all
 * pairs, which is what a network shows. So past three chains, colour is never the only cue: the chain
 * chips, the connection tooltip and the side list's chain icons all name it.
 */
const LIGHT = ['#2a78d6', '#eb6834', '#1baf7a', '#eda100', '#e87ba4', '#008300', '#6250d6', '#e34948'] as const;

const DARK = ['#3987e5', '#d95926', '#199e70', '#c98500', '#d55181', '#008300', '#9085e9', '#e66767'] as const;

/** Chains past the palette fold into one neutral, rather than a generated hue. */
const OTHER_LIGHT = '#8e8e93';

const OTHER_DARK = '#71717a';

interface ChainColors {
  /** A chain's colour, keyed by its position among every chain in the data. */
  chainColor: (chain: string) => string;
  /** The neutral grey for chains past the palette, and for a pair active on several chains. */
  neutral: ComputedRef<string>;
  /**
   * A pair on one chain takes that chain's colour, a pair on several is neutral. With `chain` picked,
   * pairs active on it take its colour and the rest are neutral.
   */
  connectionColor: (connection: InteractionConnection, chain?: string) => string;
}

/**
 * Chain and connection colours for the graph, the chain chips, and the per-chain split of a pair.
 *
 * @remarks
 * A chain's slot follows the chain, not its rank in the current view, so filtering never repaints
 * the chains that stay on screen.
 */
export function useChainColors(chains: MaybeRefOrGetter<readonly string[]>): ChainColors {
  const { isDark } = useRotkiTheme();
  const neutral = computed<string>(() => get(isDark) ? OTHER_DARK : OTHER_LIGHT);

  function chainColor(chain: string): string {
    const palette = get(isDark) ? DARK : LIGHT;
    const slot = toValue(chains).indexOf(chain);
    return slot < 0 || slot >= palette.length ? get(neutral) : palette[slot];
  }

  function connectionColor(connection: InteractionConnection, chain?: string): string {
    if (chain)
      return connection.activity.some(entry => entry.chain === chain) ? chainColor(chain) : get(neutral);
    const [only, ...rest] = connection.activity;
    return only && rest.length === 0 ? chainColor(only.chain) : get(neutral);
  }

  return { chainColor, connectionColor, neutral };
}

import type { InjectionKey } from 'vue';

/**
 * Provided by a dock section whose heading already names the kind of every job in it, such as
 * "Prices" over eighteen price jobs. A job row under it is then named by its subtitle, which is the
 * part that tells those jobs apart, rather than by a title the heading just said.
 */
export const DockKindHeadingKey: InjectionKey<() => boolean> = Symbol('dock-kind-heading');

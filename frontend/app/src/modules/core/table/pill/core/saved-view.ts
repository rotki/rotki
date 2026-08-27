import { z } from 'zod';
import { FilterBehaviours } from '@/modules/core/table/filtering';

/** One value of a stored filter: the same shapes the codec writes. */
const SavedViewValue = z.union([z.string(), z.array(z.string()), z.boolean()]);

/**
 * One entry of a view's `matches`: whatever the field codec writes for a filter-bound field, so
 * a scalar, a list, a boolean, or the behaviour-wrapped form the older filter bar produces.
 */
const SavedViewMatch = z.union([
  SavedViewValue,
  z.object({
    behaviour: z.enum(FilterBehaviours).optional(),
    values: SavedViewValue,
  }),
]);

/**
 * A named pill-bar filter set. `matches` and `params` are the two halves of the bar's transported
 * form, so a view is stored exactly as the bar already serializes itself, which is what lets a
 * view carry the param-bound pills (account, state, show-ignored, action) that the older
 * `savedFilters` shape could not express. Both are typed as the bar's two models, so a stored view
 * can be handed straight back to it.
 *
 * A `matches` value is optional so the record lines up with the bar's
 * `MatchedKeywordWithBehaviour`, whose keys are all optional: a view has to be handed back to the
 * bar as it stands.
 */
export const SavedView = z.object({
  matches: z.record(z.string(), SavedViewMatch.optional()).default({}),
  name: z.string().min(1),
  params: z.record(z.string(), SavedViewValue).default({}),
});

export type SavedView = z.infer<typeof SavedView>;

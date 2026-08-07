import type { ComputedRef } from 'vue';
import type { TagFieldOption } from '@/modules/core/table/filters/shared/tag-field';
import { useSessionMetadataStore } from '@/modules/session/use-session-metadata-store';

/**
 * The user's tags as pill options, with the colour pair each was given.
 *
 * Every table filtering on tags offers the same list from the same store, so it is read once here
 * rather than restated per table.
 */
export function useTagFieldOptions(): ComputedRef<TagFieldOption[]> {
  const { tags } = storeToRefs(useSessionMetadataStore());

  return computed<TagFieldOption[]>(() => get(tags).map(tag => ({
    name: tag.name,
    swatch: { background: `#${tag.backgroundColor}`, foreground: `#${tag.foregroundColor}` },
  })));
}

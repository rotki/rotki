import type { LocationEditPayload, LocationNode } from '@/modules/locations/use-location-tree-api';
import { z, type ZodType } from 'zod';
import { msg } from '@/message-key';
import { DEFAULT_LOCATION_ICON, isLocationIcon, type LocationIcon } from '@/modules/locations/location-icons';

export interface LocationFormState {
  name: string;
  parentIdentifier: string;
  icon: LocationIcon;
}

/** A location being created below `parentIdentifier`, or the custom location being edited. */
export type LocationFormData =
  | { readonly mode: 'add'; readonly parentIdentifier: string }
  | { readonly mode: 'edit'; readonly location: LocationNode };

export function toLocationFormState(data: LocationFormData): LocationFormState {
  if (data.mode === 'add')
    return { icon: DEFAULT_LOCATION_ICON, name: '', parentIdentifier: data.parentIdentifier };
  const { icon, name, parentIdentifier } = data.location;
  return {
    icon: isLocationIcon(icon) ? icon : DEFAULT_LOCATION_ICON,
    name,
    parentIdentifier: parentIdentifier ?? '',
  };
}

export function locationFormSchema(): ZodType<LocationFormState> {
  const required = msg.$t('location_manager.form.validation.required');
  return z.object({
    icon: z.custom<LocationIcon>(value => typeof value === 'string' && isLocationIcon(value)),
    name: z.string().trim().min(1, required),
    parentIdentifier: z.string().min(1, required),
  });
}

/** The fields of an edit that differ from the stored location, with a trimmed name. */
export function locationEditPayload(location: LocationNode, state: LocationFormState): LocationEditPayload {
  const name = state.name.trim();
  return {
    ...(name === location.name ? {} : { name }),
    ...(state.parentIdentifier === location.parentIdentifier ? {} : { parentIdentifier: state.parentIdentifier }),
    ...(state.icon === location.icon ? {} : { icon: state.icon }),
  };
}

/**
 * The locations a location can be placed below: active ones outside its own subtree. The total
 * counts, so a location can sit at the top level.
 */
export function parentCandidates(nodes: readonly LocationNode[], subtree: ReadonlySet<string>): string[] {
  return nodes.filter(node => node.isActive && !subtree.has(node.identifier)).map(node => node.identifier);
}

import type { LocationNode } from '@/modules/locations/use-location-tree-api';

export interface LocationRow {
  readonly node: LocationNode;
  /** How far below the total the location is, 0 for its children. */
  readonly depth: number;
  /** The names from below the total down to the location. */
  readonly path: string;
  /** Whether the location has rows below it that can be shown or hidden. */
  readonly hasChildren: boolean;
  /** Whether the rows below the location are shown. */
  readonly expanded: boolean;
}

export interface LocationRowsInput {
  readonly childrenOf: (identifier: string) => LocationNode[];
  readonly root: string;
  readonly showArchived: boolean;
  /** Archived locations that stay listed anyway, such as one archived a moment ago. */
  readonly keepArchived?: ReadonlySet<string>;
  readonly search: string;
  /** Whether the user left a location open; a search opens every location on the way to a match. */
  readonly isExpanded: (identifier: string) => boolean;
}

/**
 * The rows of the location manager: the tree below the total in depth-first order, children
 * sorted by name, without the subtrees of collapsed locations.
 *
 * @remarks
 * Hidden archived locations take their subtree with them, which only ever holds archived
 * locations. A search keeps the matching locations and the ancestors that lead to them, so a
 * match is always shown where it sits in the tree, collapsed or not.
 */
export function locationRows({ childrenOf, isExpanded, keepArchived, root, search, showArchived }: LocationRowsInput): LocationRow[] {
  const needle = search.trim().toLowerCase();
  const searching = needle !== '';
  const rows: LocationRow[] = [];
  const isListed = (node: LocationNode): boolean =>
    showArchived || node.isActive || (keepArchived?.has(node.identifier) ?? false);

  const visit = (node: LocationNode, depth: number, parentPath: string): boolean => {
    if (!isListed(node))
      return false;
    const path = parentPath === '' ? node.name : `${parentPath} › ${node.name}`;
    const children = childrenOf(node.identifier).filter(isListed);
    const expanded = searching || isExpanded(node.identifier);
    const index = rows.push({ depth, expanded, hasChildren: children.length > 0, node, path }) - 1;
    let keep = !searching || node.name.toLowerCase().includes(needle);
    if (expanded) {
      for (const child of children) {
        if (visit(child, depth + 1, path))
          keep = true;
      }
    }
    if (!keep)
      rows.splice(index, rows.length - index);
    return keep;
  };

  for (const child of childrenOf(root))
    visit(child, 0, '');
  return rows;
}

export interface NamePart {
  readonly text: string;
  readonly match: boolean;
}

/** A name cut around the first place a search matches it, ignoring case, to mark the match. */
export function nameParts(name: string, search: string): NamePart[] {
  const needle = search.trim().toLowerCase();
  const start = needle === '' ? -1 : name.toLowerCase().indexOf(needle);
  if (start === -1)
    return [{ match: false, text: name }];
  const end = start + needle.length;
  return [
    { match: false, text: name.slice(0, start) },
    { match: true, text: name.slice(start, end) },
    { match: false, text: name.slice(end) },
  ].filter(part => part.text !== '');
}

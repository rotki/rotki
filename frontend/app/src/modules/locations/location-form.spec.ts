import { createLocationNode as node } from '@test/utils/location-tree';
import { describe, expect, it } from 'vitest';
import {
  locationEditPayload,
  locationFormSchema,
  parentCandidates,
  toLocationFormState,
} from '@/modules/locations/location-form';

const ing = node('custom:ing', 'banks', 'ING', { icon: 'lu-landmark', isBuiltin: false });

describe('location form', () => {
  it('should start a new location below the chosen parent with the default icon', () => {
    expect(toLocationFormState({ mode: 'add', parentIdentifier: 'banks' })).toEqual({ icon: 'lu-map-pin', name: '', parentIdentifier: 'banks' });
    expect(toLocationFormState({ mode: 'edit', location: ing })).toEqual({ icon: 'lu-landmark', name: 'ING', parentIdentifier: 'banks' });
  });

  it('should demand a name and a parent, and only an icon of the list', () => {
    const issues = (state: Record<string, unknown>): string[] => {
      const result = locationFormSchema().safeParse(state);
      return result.success ? [] : result.error.issues.map(issue => issue.path.join('.'));
    };
    expect(issues({ icon: 'lu-map-pin', name: '  ', parentIdentifier: '' })).toEqual(['name', 'parentIdentifier']);
    expect(issues({ icon: 'lu-rocket', name: 'ING', parentIdentifier: 'banks' })).toEqual(['icon']);
    expect(issues({ icon: 'lu-map-pin', name: 'ING', parentIdentifier: 'banks' })).toEqual([]);
  });

  it('should send only the fields an edit changes', () => {
    expect(locationEditPayload(ing, { icon: 'lu-landmark', name: ' ING ', parentIdentifier: 'banks' })).toEqual({});
    expect(locationEditPayload(ing, { icon: 'lu-vault', name: 'ING DiBa', parentIdentifier: 'other' }))
      .toEqual({ icon: 'lu-vault', name: 'ING DiBa', parentIdentifier: 'other' });
  });

  it('should not offer an archived location or the own subtree as parent', () => {
    const nodes = [node('total', null, 'Total'), node('banks', 'total', 'Banks'), ing, node('custom:old', 'banks', 'Old', { isActive: false })];
    expect(parentCandidates(nodes, new Set(['custom:ing']))).toEqual(['total', 'banks']);
  });
});

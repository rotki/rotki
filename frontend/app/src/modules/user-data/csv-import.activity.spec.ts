import { describe, expect, it } from 'vitest';
import { csvImportActivity } from '@/modules/user-data/csv-import.activity';

describe('csv import activity ids', () => {
  it('should key an import by its source', () => {
    expect(csvImportActivity.id({ source: 'cointracking' })).toBe('csv-import:cointracking');
  });

  it('should give two sources distinct ids, so their imports run side by side', () => {
    expect(csvImportActivity.id({ source: 'cointracking' })).not.toBe(csvImportActivity.id({ source: 'cryptocom' }));
  });
});

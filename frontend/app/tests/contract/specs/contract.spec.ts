import { describe, it } from 'vitest';
import { useUsersApi } from '@/composables/api/session/users';

/*
    grep "const use.*Api" ./app/src/auto-imports.d.ts | cut -d ' ' -f4 | tr -d ':'
*/

describe('test compliance with User Api', () => {
  const api = useUsersApi();
  it('gets user profiles', async () => {
    await api.getUserProfiles();
  });
});

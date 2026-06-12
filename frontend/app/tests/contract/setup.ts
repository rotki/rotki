import process from 'node:process';
import { mockT } from '@test/i18n';
import { beforeAll, vi } from 'vitest';
import { ref } from 'vue';
import { api } from '@/modules/core/api/rotki-api';
import { contractBackendUrl, contractUsername } from './contract-env';

// i18n is a UI concern, not part of the API contract, but some zod schema
// transforms reach for useI18n — mock it the same way the unit setup does.
vi.mock('vue-i18n', () => ({
  createI18n: () => ({}),
  useI18n: () => ({
    locale: ref(''),
    t: mockT,
    te: mockT,
  }),
}));

/**
 * Points the api singleton at the live contract backend and unlocks the
 * profile user. Runs once per test file; the unlock is idempotent (an
 * already-logged-in response is accepted).
 */
beforeAll(async () => {
  api.setup(contractBackendUrl());

  const username = contractUsername();
  const response = await fetch(`${contractBackendUrl()}/api/1/users/${username}`, {
    body: JSON.stringify({
      password: process.env.CONTRACT_PASSWORD ?? '1234',
      resume_from_backup: false,
      sync_approval: 'no',
    }),
    headers: { 'Content-Type': 'application/json' },
    method: 'POST',
  });

  if (!response.ok) {
    const body = await response.text();
    if (!body.includes('logged'))
      throw new Error(`contract setup: failed to unlock user ${username}: ${response.status} ${body}`);
  }
});

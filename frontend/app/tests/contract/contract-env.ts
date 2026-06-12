import process from 'node:process';

export function contractBackendUrl(): string {
  const url = process.env.CONTRACT_BACKEND_URL;
  if (!url)
    throw new Error('CONTRACT_BACKEND_URL is not set. Run the contract tests through `pnpm run test:contract`, which boots a backend on a golden profile.');
  return url;
}

export function contractUsername(): string {
  return process.env.CONTRACT_USERNAME ?? 'small';
}

/**
 * The expected values emitted by the profile generator
 * (users/<profile>/expected.json), forwarded by the runner script.
 */
export function contractExpected(): Record<string, any> {
  const raw = process.env.CONTRACT_EXPECTED;
  if (!raw)
    throw new Error('CONTRACT_EXPECTED is not set. Run the contract tests through `pnpm run test:contract`.');
  return JSON.parse(raw);
}

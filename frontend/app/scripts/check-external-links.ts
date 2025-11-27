import process from 'node:process';
import consola from 'consola';
import z from 'zod/v4';
import { externalLinks } from '../shared/external-links';

const Release = z.object({
  tag_name: z.string(),
});

interface LinkResult {
  url: string;
  originalUrl: string;
  key: string;
  success: boolean;
  statusCode?: number;
  error?: string;
}

async function processDynamicUrl(url: string): Promise<string> {
  if (url.includes('v$version')) {
    const response = await fetch('https://api.github.com/repos/rotki/rotki/releases/latest');
    const { tag_name } = Release.parse(await response.json());

    // Format dynamic URL and replace with valid value.
    return url.replace('v$version', tag_name);
  }
  else if (url.includes('$symbol')) {
    return url.replace('$symbol', 'usdc');
  }

  return url;
}

async function checkLink(rawUrl: string, key: string): Promise<LinkResult> {
  const url = await processDynamicUrl(rawUrl);
  try {
    const response = await fetch(url);
    if ((response.status >= 200 && response.status < 300) || [401, 403].includes(response.status)) {
      consola.debug(`✓ External link ${url} returned a ${response.status} that is considered successful.`);
      return {
        url,
        originalUrl: rawUrl,
        key,
        success: true,
        statusCode: response.status,
      };
    }
    else {
      consola.error(`✗ External link ${url} returned a status code: ${response.status} that is considered a failure.`);
      return {
        url,
        originalUrl: rawUrl,
        key,
        success: false,
        statusCode: response.status,
      };
    }
  }
  catch (error: any) {
    consola.error(`✗ Error checking link ${url}: ${error.message}`);
    return {
      url,
      originalUrl: rawUrl,
      key,
      success: false,
      error: error.message,
    };
  }
}

function getFlattenedKeysAndValues(obj: Record<string, any>, prefix = ''): Array<{ key: string; value: string }> {
  const result: Array<{ key: string; value: string }> = [];

  for (const [key, value] of Object.entries(obj)) {
    const fullKey = prefix ? `${prefix}.${key}` : key;

    if (typeof value === 'object' && value !== null) {
      result.push(...getFlattenedKeysAndValues(value, fullKey));
    }
    else if (typeof value === 'string') {
      result.push({ key: fullKey, value });
    }
  }

  return result;
}

async function checkLinksInBatches(links: Array<{ key: string; value: string }>, batchSize: number): Promise<LinkResult[]> {
  const results: LinkResult[] = [];

  for (let i = 0; i < links.length; i += batchSize) {
    const batch = links.slice(i, i + batchSize);
    const batchPromises = batch.map(async ({ key, value }) => checkLink(value, key));

    consola.info(`Checking batch ${Math.floor(i / batchSize) + 1} of ${Math.ceil(links.length / batchSize)} (${batch.length} links)...`);

    const batchResults = await Promise.allSettled(batchPromises);

    for (const result of batchResults) {
      if (result.status === 'fulfilled') {
        results.push(result.value);
      }
      else {
        consola.error(`Unexpected error in promise: ${result.reason}`);
      }
    }
  }

  return results;
}

// Process links with limited parallelization
const linksWithKeys = getFlattenedKeysAndValues(externalLinks);
const BATCH_SIZE = 5; // Process 5 links at a time

consola.info(`Starting to check ${linksWithKeys.length} external links in batches of ${BATCH_SIZE}...`);

// eslint-disable-next-line no-void,unicorn/prefer-top-level-await
void checkLinksInBatches(linksWithKeys, BATCH_SIZE).then(async (linkResults) => {
  const failures = linkResults.filter(result => !result.success);

  if (failures.length > 0) {
    consola.box('FAILED LINKS SUMMARY');
    consola.fail(`Total failures: ${failures.length} out of ${linkResults.length} links`);

    for (const failure of failures) {
      consola.error('');
      consola.error(`✗ Key: ${failure.key}`);
      consola.log(`  Original URL: ${failure.originalUrl}`);
      consola.log(`  Processed URL: ${failure.url}`);
      if (failure.statusCode) {
        consola.log(`  Status Code: ${failure.statusCode}`);
      }
      if (failure.error) {
        consola.log(`  Error: ${failure.error}`);
      }
    }

    consola.error('');
    consola.fail('Link verification failed!');
    process.exit(1);
  }
  else {
    consola.box('SUCCESS');
    consola.success(`All ${linkResults.length} external links verified successfully!`);
    process.exit(0);
  }
});

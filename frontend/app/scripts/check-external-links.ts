import process from 'node:process';
import { externalLinks } from '../shared/external-links';

async function processDynamicUrl(url: string): Promise<string> {
  if (url.includes('v$version')) {
    const response = await fetch('https://api.github.com/repos/rotki/rotki/releases/latest');
    const { tag_name } = await response.json();

    // Format dynamic URL and replace with valid value.
    return url.replace('v$version', tag_name);
  }
  else if (url.includes('$symbol')) {
    return url.replace('$symbol', 'usdc');
  }

  return url;
}

async function checkLink(rawUrl: string): Promise<void> {
  const url = await processDynamicUrl(rawUrl);
  try {
    const response = await fetch(url);
    if (response.status === 200) {
      console.log(`External link ${url} returned a 200 status code.`);
    }
    else {
      console.error(`External link ${url} returned a non-200 status code: ${response.status}`);
      process.exit(1); // Exit with an error status code
    }
  }
  catch (error: any) {
    console.error(`Error checking link ${url}: ${error.message}`);
    process.exit(1); // Exit with an error status code
  }
}

function getFlattenedValues(obj: Record<string, any>): string[] {
  return Object.values(obj).flatMap(value =>
    typeof value === 'object' && value !== null ? Object.values(value) : value,
  );
}

// Create an array of promises
const linkCheckPromises = getFlattenedValues(externalLinks).map(checkLink);

// Wait for all promises to settle
// eslint-disable-next-line no-void,unicorn/prefer-top-level-await
void Promise.all(linkCheckPromises).then(() => {
  console.log('\u001B[32m', 'All external links verified');
  process.exit(0);
});

import { camelCase } from 'lodash-es';
import { pslSuffixes } from '@/data/psl';
import { etherscanLinks, externalLinks } from '@/data/external-links';
import { isEtherscanKey } from '@/types/external';
import type { RouteLocationRaw } from 'vue-router';

export function getDomain(str: string): string {
  const pattern = /^(?:https?:)?(?:\/\/)?(?:[^\n@]+@)?(?:www\.)?([^\n/:]+)/;
  const exec = pattern.exec(str);

  const withSubdomain = exec?.[1];

  if (!withSubdomain)
    return str;

  const parts = withSubdomain.split('.');
  const length = parts.length;
  let i = length - 1;
  let domain = withSubdomain;

  while (i > 0) {
    const used = parts.slice(-i).join('.');
    const found = pslSuffixes.has(used);

    if (found)
      break;

    domain = used;
    i -= 1;
  }

  return domain;
}

/**
 * Returns the registration url of a specified Etherscan location and a path to the local page
 * @param {string} location
 * @returns {{external: string, route: RouteLocationRaw} | undefined}
 */
export function getEtherScanRegisterUrl(location: string): { external: string; route: RouteLocationRaw } | undefined {
  const camelCaseLocation = camelCase(location);

  if (isEtherscanKey(camelCaseLocation)) {
    const data = etherscanLinks[camelCaseLocation];
    return {
      external: data,
      route: { path: '/api-keys/external', hash: `#${location}` },
    };
  }

  logger.warn(`Unsupported etherscan location: '${location}'`);
  return undefined;
}

export function getTheGraphRegisterUrl(): { external: string; route: RouteLocationRaw } {
  return {
    external: externalLinks.applyTheGraphApiKey,
    route: { path: '/api-keys/external', hash: `#thegraph` },
  };
}

/**
 * Returns the registration url of a specified service location and a path to the local page
 * @param {string} service
 * @param {string} location
 * @returns {undefined | {external: string, route: RouteLocationRaw}}
 */
export function getServiceRegisterUrl(service: string, location: string) {
  switch (service) {
    case 'etherscan':
      return getEtherScanRegisterUrl(location);
    case 'thegraph':
      return getTheGraphRegisterUrl();
    default:
      logger.warn(`Unsupported service: '${service}'`);
      return undefined;
  }
}

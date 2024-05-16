import { camelCase } from 'lodash-es';
import { pslSuffixes } from '@/data/psl';
import { Routes } from '@/router/routes';
import { etherscanLinks, externalLinks } from '@/data/external-links';
import { isEtherscanKey } from '@/types/external';

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
 * @returns {{external: string, route: {path: string, hash: string}} | {}}
 */
export function getEtherScanRegisterUrl(location: string) {
  const camelCaseLocation = camelCase(location);

  if (isEtherscanKey(camelCaseLocation)) {
    const data = etherscanLinks[camelCaseLocation];
    return {
      external: data,
      route: { path: Routes.API_KEYS_EXTERNAL_SERVICES, hash: `#${location}` },
    };
  }

  logger.warn(`Unsupported etherscan location: '${location}'`);
  return {};
}

export function getTheGraphRegisterUrl() {
  return {
    external: externalLinks.applyTheGraphApiKey,
    route: { path: Routes.API_KEYS_EXTERNAL_SERVICES, hash: `#thegraph` },
  };
}

/**
 * Returns the registration url of a specified service location and a path to the local page
 * @param {string} service
 * @param {string} location
 * @returns {{} | {external: string, route: {path: string, hash: string}}}
 */
export function getServiceRegisterUrl(service: string, location: string) {
  switch (service) {
    case 'etherscan':
      return getEtherScanRegisterUrl(location);
    case 'thegraph':
      return getTheGraphRegisterUrl();
    default:
      logger.warn(`Unsupported service: '${service}'`);
      return {};
  }
}

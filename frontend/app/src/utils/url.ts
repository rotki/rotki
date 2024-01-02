import { pslSuffixes } from '@/data/psl';
import { Routes } from '@/router/routes';
import { externalLinks } from '@/data/external-links';

export const getDomain = (str: string): string => {
  const pattern = /^(?:https?:)?(?:\/\/)?(?:[^\n@]+@)?(?:www\.)?([^\n/:]+)/;
  const exec = pattern.exec(str);

  const withSubdomain = exec?.[1];

  if (!withSubdomain) {
    return str;
  }

  const parts = withSubdomain.split('.');
  const length = parts.length;
  let i = length - 1;
  let domain = withSubdomain;

  while (i > 0) {
    const used = parts.slice(-i).join('.');
    const found = pslSuffixes.has(used);

    if (found) {
      break;
    }

    domain = used;
    i -= 1;
  }

  return domain;
};

const { etherscan } = externalLinks;

/**
 * Returns the registration url of a specified Etherscan location and a path to the local page
 * @param {string} location
 * @returns {{external: string, route: {path: string, hash: string}} | {}}
 */
export const getEtherScanRegisterUrl = (location: string) => {
  switch (location) {
    case 'optimism':
      return {
        external: etherscan.optimism,
        route: { path: Routes.API_KEYS_EXTERNAL_SERVICES, hash: `#${location}` }
      };
    case 'ethereum':
      return {
        external: etherscan.ethereum,
        route: { path: Routes.API_KEYS_EXTERNAL_SERVICES, hash: `#${location}` }
      };
    case 'polygon_pos':
      return {
        external: etherscan.polygonPos,
        route: {
          path: Routes.API_KEYS_EXTERNAL_SERVICES,
          hash: `#${location}`
        }
      };
    case 'arbitrum_one':
      return {
        external: etherscan.arbitrum,
        route: {
          path: Routes.API_KEYS_EXTERNAL_SERVICES,
          hash: `#${location}`
        }
      };
    case 'base':
      return {
        external: etherscan.base,
        route: { path: Routes.API_KEYS_EXTERNAL_SERVICES, hash: `#${location}` }
      };
    case 'gnosis':
      return {
        external: etherscan.gnosis,
        route: { path: Routes.API_KEYS_EXTERNAL_SERVICES, hash: `#${location}` }
      };
    default:
      logger.warn(`Unsupported etherscan location: '${location}'`);
      return {};
  }
};

/**
 * Returns the registration url of a specified service location and a path to the local page
 * @param {string} service
 * @param {string} location
 * @returns {{} | {external: string, route: {path: string, hash: string}}}
 */
export const getServiceRegisterUrl = (service: string, location: string) => {
  switch (service) {
    case 'etherscan':
      return getEtherScanRegisterUrl(location);
    default:
      logger.warn(`Unsupported service: '${service}'`);
      return {};
  }
};

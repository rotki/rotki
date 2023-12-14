interface ExternalLinksObject {
    usageGuide: string;
    faq: string;
    changeLog: string
  }

export const externalLinks: ExternalLinksObject = {
    usageGuide: 'https://rotki.readthedocs.io/en/latest/usage_guide.html',
    faq: 'https://rotki.readthedocs.io/en/latest/faq.html',
    changeLog: 'https://rotki.readthedocs.io/en/latest/changelog.html'

  } as const;
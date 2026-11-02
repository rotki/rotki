# FinTS bank directory maintenance

The bundled catalog is deliberately small and manually vetted. Each endpoint and bank code must be
confirmed on pages published by the bank, recorded in `fints-bank-directory.json`, and covered by
the directory validation test. Bump the catalog version whenever a record changes.

Do not generate the shipped catalog from AqBanking's `de.tar.bz2`. AqBanking's bank-info README
states that its German data combines the Bundesbank BLZ file with the registered-product FinTS
institute CSV. The [official FinTS usage terms](https://www.fints.org/de/hersteller/bankenliste)
prohibit redistribution of that institute list as part of a software product. AqBanking's repository
license does not establish separate redistribution rights for that upstream data.

Current bank-published sources:

- [BBBank HBCI endpoint](https://www.bbbank.de/privatkunden/girokonto/banking/hbci.html) and
  [BBBank BLZ](https://www.bbbank.de/meine-bbbank/investor-relations/kennzahlen.html)
- [comdirect FinTS endpoint](https://www.comdirect.de/cms/sicherheit-software-banking-fints.html)
  and [comdirect BLZ list](https://www.comdirect.de/business-partners/faq.html)
- [GLS Bank FinTS endpoint and BLZ](https://www.gls.de/konten-karten/zahlungsverkehr/sepa-zahlungsverkehr/daten-zum-onlinebanking/)

Before changing a record, check that the page still identifies an HTTPS PIN/TAN endpoint, not an
HBCI chip-card host. Never copy records from the restricted FinTS list. Banks without a verified
endpoint remain available through the manual-details flow.

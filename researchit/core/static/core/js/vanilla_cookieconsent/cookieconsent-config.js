/**
 * All config. options available here:
 * https://cookieconsent.orestbida.com/reference/configuration-reference.html
 */
CookieConsent.run({

  cookie: {
    name: '_cookie_consent',
  },

  guiOptions: {
    consentModal: {
      layout: 'cloud inline',
      position: 'bottom center',
      equalWeightButtons: true,
      flipButtons: false
    },
    preferencesModal: {
      layout: 'box',
      equalWeightButtons: true,
      flipButtons: false
    }
  },

  categories: {
    necessary: {
      enabled: true,
      readOnly: true
    },
  },

  language: {
    default: 'en',
    translations: {
      en: {
        consentModal: {
          title: 'Cookie Notice',
          description: 'We only use cookies that are strictly necessary for this website to function. No tracking or advertising cookies are used.',
          acceptAllBtn: 'Got it',
          // acceptNecessaryBtn: 'Reject all',
          showPreferencesBtn: 'Learn more',
          // closeIconLabel: 'Reject all and close modal',
          footer: `
                        <a href="/impressum/" target="_blank">Impressum</a>
                        <a href="/privacy/" target="_blank">Privacy Policy</a>
                    `,
        },
        preferencesModal: {
          title: 'Cookie Information',
          acceptNecessaryBtn: 'Got it',
          closeIconLabel: 'Close',
          serviceCounterLabel: 'Service|Services',
          sections: [
            {
              title: 'About Cookies on our site',
              description: `This website only uses essential cookies required for basic functionality, such as keeping you logged in and maintaining security. We do not use any cookies for analytics, advertising, or tracking.`,
            },
            {
              title: 'Strictly Necessary',
              description: 'These cookies are required for the website to work and cannot be disabled. They do not store any personally identifiable information.',
              linkedCategory: 'necessary',
              cookieTable: {
                headers: {
                  name: 'Cookie',
                  domain: 'Domain',
                  desc: 'Description'
                },
                body: [
                  {
                    name: 'sessionid',
                    domain: location.hostname,
                    desc: 'Manages your login session. Required to access your account and personal settings.',
                  },
                  {
                    name: 'csrftoken',
                    domain: location.hostname,
                    desc: 'Security cookie that prevents malicious sites from performing actions on your behalf.',
                  },
                  {
                    name: '_cookie_consent',
                    domain: location.hostname,
                    desc: 'Stores your cookie preferences so this notice is not shown on every visit.'
                  }
                ]
              }
            },
          ]
        }
      }
    }
  }
});

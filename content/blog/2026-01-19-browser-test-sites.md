---
title: "Test sites for browser developers"
updated: 2026-01-29T16:39:59-05:00
draft: false
taxonomies:
  tags: ["workflow", "mozilla"]
  categories: ["blog"]
extra:
  hide_table_of_contents: true
---

Working on the mobile Firefox team gives you the opportunity to touch on many different parts of the browser space. You often need to test the interaction between web content and the application integration's to another component, say for example, a site registering for a WebPush subscription and Firefox using Firebase Cloud Messaging to deliver the encrypted message to the end-user. Hunting around for an example to validate everything fine and dandy takes time.



Sometimes a simple test site for your use case is helpful for initial validation or comparison against other browsers.

Below is a list of tests that I've used in the past (in no particular order):

- [badssl.com](https://badssl.com)
  - Great for testing out the various error pages that a browser can show.
- [(Safe) Safe Browsing Testing Links ](https://testsafebrowsing.appspot.com/)
  - For making sure we are still using the [Safe Browsing](https://safebrowsing.google.com/) list correctly.
- [WebAuthn / Passkeys & PRF Demo](https://webauthn-passkeys-prf-demo.explore.corbado.com/)
  - For [WebAuthn](https://developer.mozilla.org/en-US/docs/Web/API/Web_Authentication_API) login/registration, but also includes PRF extension support.
- [Web Push: Data Encryption Test Page](https://mozilla-services.github.io/WebPushDataTestPage/)
  - Push notifications requires a server to send a notification to the client (not the same as a WebNotification), so you can use this WebPush test site for validating just that.
- [Simple Push Demo](https://simple-push-demo.vercel.app/)
  - Similar to the above, but prettier.
- [Test of HTML5 localStorage and sessionStorage persistence - sharonminsuk.com](http://www.sharonminsuk.com/code/storage-test.html)
  - When you have to verify that [`localStorage`](https://developer.mozilla.org/en-US/docs/Web/API/Window/localStorage) is truly gone. This is especially helpful for Firefox Focus where private browsing is the primary feature.
- [`<input>`: The HTML Input element - MDN](https://developer.mozilla.org/en-US/docs/Web/HTML/Reference/Elements/input)
  - There are Too Many™ different prompt and input element types. The MDN docs have the best collection of all of them.

### Forms and Autocomplete
There are various form types and various heuristics to trigger completion options, so they deserve their own section. The more (test sites) the merrier!
- [Registration, Login and Change Forms - MattN](https://bugs.mattn.ca/pwmgr/login_and_change_form.html)
  - Web forms come in all shapes and sizes. Some simple forms to see if we can detect a login/registration form and fill a login entry into them.
- [fill.dev](https://fill.dev/form/login-simple)
  - More forms, but also includes credit card and address form filling.
- [daleharvey.github.io/testapp](https://daleharvey.github.io/testapp/)
  - Good for sanity testing simple forms, links that have same/different origins, or (location) permission prompts.
- [Sign-Up & Login Forms - Dimi](https://dimidl.github.io/signup/test.html)
  - Sign-up and login forms behave differently, so they are handy to test separately. For example, autofilling a generated password is useful on a registration form but not on a login one.


### Make your own

If you need to make your own, try to write out the code yourself so you can understand the reduced test case. If it's not straight-forward, try using the [Testcase Reducer by Thomas Wisniewski](https://addons.mozilla.org/en-CA/firefox/addon/testcase-reducer/).

{{ comments(host="mindly.social", username="jonalmeida", id=115937256635328128) }}

<route lang="yaml">
meta:
  layout: landing
  requiresAuth: false
</route>

<!--
  TEMPLATE - adapt to your product and processors, and have it reviewed by a
  lawyer before launch. Company details come from src/brand.ts.
-->
<template>
  <div class="flex justify-center px-4 py-12">
    <div class="max-w-2xl w-full text-sm text-slate-600 space-y-4">
      <h1 class="text-lg font-semibold text-slate-900">Privacy Policy</h1>
      <p class="text-xs text-slate-600">Last updated: {{ LAST_UPDATED }}</p>

      <p>
        This Privacy Policy describes how {{ BRAND.name }} ("we", "us", "our") collects, uses, and
        protects your personal data when you visit our website or use our services ("Service"). We
        process personal data in accordance with Regulation (EU) 2016/679 (GDPR) and applicable
        Danish data protection law.
      </p>

      <h2 class="font-semibold text-slate-900">Data Controller</h2>
      <p>
        The data controller responsible for your personal data is:<br />
        <strong>{{ BRAND.legalEntity.name }}</strong
        ><br />
        {{ BRAND.legalEntity.registrationLabel }}: {{ BRAND.legalEntity.registrationNumber }}<br />
        {{ BRAND.legalEntity.address }}<br />
        Email: {{ BRAND.supportEmail }}
      </p>

      <h2 class="font-semibold text-slate-900">Data We Collect</h2>
      <p>We may collect the following types of information:</p>
      <ul class="list-disc pl-5 space-y-1">
        <li><strong>Personal data</strong> - your name, email address and billing information</li>
        <li>
          <strong>Customer data</strong> - data you or your users input into the system as part of
          using the Service, stored and processed only to provide the Service and related services
          to you.
        </li>
        <li>
          <strong>Usage data</strong> - information about how you interact with the Service, such as
          log files, IP addresses, browser types, device information, and pages visited.
        </li>
      </ul>

      <h2 class="font-semibold text-slate-900">Controller and Processor Roles</h2>
      <p>
        For personal data about third parties that you or your users store in the Service, you are
        the data controller and we act as your data processor. That processing is governed by the
        Data Processing section of our
        <RouterLink :to="localePath('terms')" class="underline">Terms of Service</RouterLink>. For
        account, billing, and usage data we are the data controller.
      </p>

      <h2 class="font-semibold text-slate-900">Legal Basis for Processing</h2>
      <ul class="list-disc pl-5 space-y-1">
        <li>
          <strong>Performance of a contract</strong> (Art. 6(1)(b)) - account data and usage data
          are processed to deliver the service you have subscribed to.
        </li>
        <li>
          <strong>Legal obligation</strong> (Art. 6(1)(c)) - billing records are retained to comply
          with Danish bookkeeping law (bogføringsloven).
        </li>
        <li>
          <strong>Legitimate interest</strong> (Art. 6(1)(f)) - transactional emails (password
          reset, notifications) and service-related communications are sent on the basis of our
          legitimate interest in operating the service.
        </li>
      </ul>

      <h2 class="font-semibold text-slate-900">Data Processors and Third-Party Services</h2>
      <p>
        We share personal data only with processors necessary to deliver the service. All processors
        are bound by data processing agreements (DPAs) in accordance with Art. 28 GDPR:
      </p>
      <ul class="list-disc pl-5 space-y-1">
        <li>
          <strong>Stripe</strong> - payment processing. Receives billing contact information and
          processes card data on our behalf. EU customers are served by Stripe Payments Europe, Ltd.
          (Ireland).
        </li>
        <li>
          <strong>Hetzner Online GmbH</strong> - cloud infrastructure and hosting. Stores and
          processes data on servers located in the EU on our behalf.
        </li>
        <li>
          <strong>Transactional email provider</strong> - delivery of system emails. Receives your
          email address and the content of system notifications. The provider is located outside the
          EU/EEA; see International Data Transfers below.
        </li>
        <li>
          <strong>tawk.to inc.</strong> - live chat support. Loaded only with your consent via the
          cookie banner; receives the messages you send and technical data required to operate the
          chat session.
        </li>
      </ul>
      <p>We do not sell or share your personal data with third parties for marketing purposes.</p>

      <h2 class="font-semibold text-slate-900">International Data Transfers</h2>
      <p>
        Some of our processors transfer personal data outside the EU/EEA. Transfers to Stripe's US
        entities are safeguarded by the EU-US Data Privacy Framework and Standard Contractual
        Clauses (SCCs) approved by the European Commission. Transfers to our transactional email
        provider and to tawk.to (US) are safeguarded by Standard Contractual Clauses. In all cases
        an adequate level of protection for your data is ensured.
      </p>

      <h2 class="font-semibold text-slate-900">Cookies, Analytics, and Chat</h2>
      <p>
        We use a session cookie strictly necessary for authentication. We do not use advertising or
        third-party tracking cookies.
      </p>
      <p>
        For web statistics we use a self-hosted, cookieless analytics tool running on our own
        EU-hosted infrastructure. It stores nothing on your device, collects only aggregated usage
        statistics, and shares no data with third parties.
      </p>
      <p>
        Our website offers an optional live chat (Tawk.to). The chat widget is loaded only if you
        accept optional cookies in our cookie banner; until then no data is shared with the chat
        provider. When loaded, Tawk.to sets cookies required to operate the chat session. Your
        choice is stored on your device for up to 12 months, and you can change it at any time via
        "Cookie settings" in the page footer.
      </p>

      <h2 class="font-semibold text-slate-900">Data Retention</h2>
      <p>
        Account and usage data is retained for as long as your account is active. Audit logs,
        including IP addresses, are kept while your account is active and are included in your data
        export. When an account is deleted it is permanently purged, including audit logs, after a
        30-day grace period. Billing records are retained for 5 years from the end of the financial
        year they concern, to comply with Danish bookkeeping requirements.
      </p>

      <h2 class="font-semibold text-slate-900">Security</h2>
      <p>
        We protect personal data with appropriate technical and organisational measures (Art. 32
        GDPR), including encryption in transit (TLS), role-based access controls, and hosting on
        EU-located infrastructure.
      </p>

      <h2 class="font-semibold text-slate-900">Automated Decision-Making</h2>
      <p>
        We do not use your personal data for automated decision-making or profiling within the
        meaning of Art. 22 GDPR.
      </p>

      <h2 class="font-semibold text-slate-900">Your Rights</h2>
      <p>Under GDPR you have the right to:</p>
      <ul class="list-disc pl-5 space-y-1">
        <li>Access the personal data we hold about you</li>
        <li>Rectify inaccurate data</li>
        <li>Erase your data ("right to be forgotten")</li>
        <li>Export your data in a portable format</li>
        <li>Object to or restrict certain processing activities</li>
        <li>
          Withdraw consent where processing is based on consent - for optional cookies, use "Cookie
          settings" in the page footer
        </li>
        <li>
          Lodge a complaint with the Danish Data Protection Agency (Datatilsynet),
          <a
            href="https://www.datatilsynet.dk"
            target="_blank"
            rel="noopener noreferrer"
            class="underline"
            >www.datatilsynet.dk</a
          >
        </li>
      </ul>
      <p>
        You can exercise these rights from your account settings under
        <RouterLink to="/settings/privacy" class="underline">Privacy &amp; Data</RouterLink>, or by
        contacting us at {{ BRAND.supportEmail }}.
      </p>

      <h2 class="font-semibold text-slate-900">Changes to This Policy</h2>
      <p>
        We may update this policy from time to time. Material changes will be announced by email and
        reflected in the "Last updated" date at the top of this page.
      </p>

      <h2 class="font-semibold text-slate-900">Contact</h2>
      <p>For privacy-related inquiries please contact us at {{ BRAND.supportEmail }}</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { BRAND } from '@/brand'
import { useLocalePath } from '@/platform/composables/useLocalePath'

const LAST_UPDATED = '13 September 2026'

const { localePath } = useLocalePath()
</script>

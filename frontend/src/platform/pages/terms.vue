<route lang="yaml">
meta:
  layout: landing
  requiresAuth: false
</route>

<!--
  TEMPLATE - adapt to your product and have it reviewed by a lawyer before
  launch. Company details come from src/brand.ts.
-->
<template>
  <div class="flex justify-center px-4 py-12">
    <div class="max-w-2xl w-full text-sm text-slate-600 space-y-4">
      <h1 class="text-lg font-semibold text-slate-900">Terms of Service</h1>
      <p class="text-xs text-slate-600">Last updated: {{ LAST_UPDATED }}</p>

      <p>
        These Terms of Service govern your use of {{ BRAND.name }} ("the Service"). By creating an
        account you confirm that you are acting in the course of a business and not as a consumer,
        and that you agree to these terms. The Service is intended exclusively for business
        customers (B2B).
      </p>

      <h2 class="font-semibold text-slate-900">Provider</h2>
      <p>
        The Service is provided by:<br />
        <strong>{{ BRAND.legalEntity.name }}</strong
        ><br />
        {{ BRAND.legalEntity.registrationLabel }}: {{ BRAND.legalEntity.registrationNumber }}<br />
        {{ BRAND.legalEntity.address }}<br />
        Email: {{ BRAND.supportEmail }}
      </p>

      <h2 class="font-semibold text-slate-900">The Service</h2>
      <p>
        {{ BRAND.name }} is a software-as-a-service product provided over the internet. Features
        available to you depend on your subscription plan. We may develop, change or discontinue
        features of the Service over time.
      </p>

      <h2 class="font-semibold text-slate-900">Acceptable Use</h2>
      <p>
        You agree not to use the Service for illegal purposes, to infringe intellectual property
        rights, to distribute malicious software, or to interfere with the Service's operation or
        security.
      </p>

      <h2 class="font-semibold text-slate-900">Account Responsibility</h2>
      <p>
        You are responsible for maintaining the confidentiality of your account credentials and for
        all activity that occurs under your account and organisation.
      </p>

      <h2 class="font-semibold text-slate-900">Subscription and Payment</h2>
      <p>
        The Service offers a free plan with limited functionality and paid subscription plans. Paid
        subscriptions are billed in advance on a recurring basis. Prices are shown excluding VAT
        where applicable. Payments are processed by Stripe.
      </p>
      <p>
        Each organisation may use one free trial of a paid plan. No payment card is required to
        start a trial. If no payment method has been added when the trial ends, the organisation is
        moved to the free plan.
      </p>
      <p>
        You may cancel a paid subscription at any time from your billing settings. Cancellation
        takes effect at the end of the current billing period; until then the subscription remains
        active and may be resumed. We do not offer refunds for partial subscription periods except
        where required by applicable law.
      </p>
      <p>
        If a recurring payment fails, we will retry the charge and notify you. Access to paid
        features is retained during a short grace period; if payment is still not received, the
        organisation is moved to the free plan.
      </p>
      <p>
        We reserve the right to change pricing with at least 30 days' notice. Continued use of the
        Service after a price change takes effect constitutes acceptance of the new price.
      </p>

      <h2 class="font-semibold text-slate-900">Intellectual Property and Customer Data</h2>
      <p>
        You retain all rights to the data you and your users input into the Service. We claim no
        ownership of it and use it only to provide the Service. During your subscription you are
        granted a limited, non-exclusive, non-transferable licence to use the Service. The Service
        itself, including its software, design, and branding, remains our property.
      </p>

      <h2 class="font-semibold text-slate-900">Data Processing</h2>
      <p>
        Where you store personal data about third parties in the Service, you act as data controller
        for that personal data and we act as your data processor within the meaning of Art. 28 GDPR.
        In that capacity we: process the data only to provide the Service and on your documented
        instructions; ensure persons authorised to process the data are bound by confidentiality;
        apply appropriate technical and organisational security measures; engage only the
        sub-processors listed in our
        <RouterLink :to="localePath('privacy')" class="underline">Privacy Policy</RouterLink> and
        will notify you of intended changes to that list; assist you, insofar as reasonably
        possible, in responding to data subject requests; and delete the data upon termination in
        accordance with our Privacy Policy.
      </p>

      <h2 class="font-semibold text-slate-900">Service Availability</h2>
      <p>
        We strive to maintain high availability but do not guarantee uninterrupted access. Scheduled
        maintenance and outages at third-party providers may affect the Service without constituting
        a breach of these terms.
      </p>

      <h2 class="font-semibold text-slate-900">Limitation of Liability</h2>
      <p>
        To the fullest extent permitted by applicable law, our total liability to you for any claim
        arising from your use of the Service shall not exceed the subscription fees paid by you in
        the three months preceding the event giving rise to the claim. We are not liable for
        indirect or consequential losses or loss of profit.
      </p>

      <h2 class="font-semibold text-slate-900">Force Majeure</h2>
      <p>
        We are not liable for failures or delays caused by circumstances beyond our reasonable
        control, including outages at infrastructure providers, regulatory changes, or other events
        outside our control.
      </p>

      <h2 class="font-semibold text-slate-900">Termination</h2>
      <p>
        We reserve the right to suspend or terminate accounts that violate these terms. You may
        delete your account at any time from your account settings. Upon termination your data is
        permanently purged after a 30-day grace period, in accordance with our
        <RouterLink :to="localePath('privacy')" class="underline">Privacy Policy</RouterLink>.
      </p>

      <h2 class="font-semibold text-slate-900">Changes to Terms</h2>
      <p>
        We may update these terms from time to time. For material changes we will provide at least
        14 days notice by email; price changes follow the 30-day notice period described above.
        Continued use of the Service after the notice period constitutes acceptance of the revised
        terms.
      </p>

      <h2 class="font-semibold text-slate-900">Governing Law and Jurisdiction</h2>
      <p>
        These terms are governed by Danish law. Any dispute arising from or in connection with these
        terms shall be brought before the Danish courts, with the district court of our registered
        office as the court of first instance.
      </p>

      <h2 class="font-semibold text-slate-900">Miscellaneous</h2>
      <p>
        If any provision of these terms is held invalid or unenforceable, the remaining provisions
        remain in full force. You may not assign your rights or obligations under these terms
        without our prior written consent; we may assign them in connection with a merger,
        acquisition, or sale of assets.
      </p>

      <h2 class="font-semibold text-slate-900">Contact</h2>
      <p>For questions about these terms please contact us at {{ BRAND.supportEmail }}</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { BRAND } from '@/brand'
import { useLocalePath } from '@/platform/composables/useLocalePath'

const LAST_UPDATED = '13 September 2026'

const { localePath } = useLocalePath()
</script>

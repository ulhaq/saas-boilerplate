/**
 * Posts `form[data-api]` forms to the backend as JSON. The site's nginx (and
 * the dev server) proxy `/v1` to the API, so requests are same-origin and need
 * no CORS. Status copy comes from the form's `data-*` attributes so the
 * script stays locale-agnostic.
 */
function bind(form: HTMLFormElement) {
  const status = form.querySelector<HTMLElement>('[data-status]')
  const button = form.querySelector<HTMLButtonElement>('button[type="submit"]')
  const { api, sending, success, error, rateLimited } = form.dataset

  const show = (kind: 'ok' | 'error', text = '') => {
    if (!status) return
    status.dataset.kind = kind
    status.textContent = text
  }

  form.addEventListener('submit', async (event) => {
    event.preventDefault()
    if (!api || !button) return

    // Empty optional fields are omitted rather than sent as "".
    const payload = Object.fromEntries(
      [...new FormData(form).entries()].filter(([, value]) => String(value).trim() !== ''),
    )

    const label = button.textContent
    button.disabled = true
    if (sending) button.textContent = sending
    show('ok')

    try {
      const response = await fetch(api, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })
      if (response.status === 429) throw new Error(rateLimited)
      if (!response.ok) throw new Error(error)
      form.reset()
      form.dataset.sent = 'true'
      show('ok', success)
    } catch (err) {
      show('error', err instanceof Error && err.message ? err.message : error)
    } finally {
      button.disabled = false
      button.textContent = label
    }
  })
}

document.querySelectorAll<HTMLFormElement>('form[data-api]').forEach(bind)

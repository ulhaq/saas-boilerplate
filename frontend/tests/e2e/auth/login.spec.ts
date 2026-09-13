import { test, expect } from '@playwright/test'

test.describe('Login page', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/login')
  })

  test('renders email, password fields and sign in button', async ({ page }) => {
    await expect(page.locator('#email')).toBeVisible()
    await expect(page.locator('#password')).toBeVisible()
    await expect(page.getByRole('button', { name: 'Sign in' })).toBeVisible()
    await expect(page.getByRole('link', { name: 'Forgot password?' })).toBeVisible()
  })

  test('empty submit does nothing (no fields, no navigation)', async ({ page }) => {
    await page.getByRole('button', { name: 'Sign in' }).click()
    await expect(page).toHaveURL('/login')
  })

  test('wrong password shows error message', async ({ page }) => {
    await page.locator('#email').fill('admin@example.org')
    await page.locator('#password').fill('wrongpassword')
    await page.getByRole('button', { name: 'Sign in' }).click()
    await expect(page.locator('.text-destructive')).toBeVisible()
  })

  test('valid credentials redirect to dashboard', async ({ page }) => {
    await page.locator('#email').fill('admin@example.org')
    await page.locator('#password').fill('password')
    await page.getByRole('button', { name: 'Sign in' }).click()
    await page.waitForURL('/')
    await expect(page).toHaveURL('/')
  })

  test('respects redirect query param after login', async ({ page }) => {
    await page.goto('/login?redirect=/settings')
    await page.locator('#email').fill('admin@example.org')
    await page.locator('#password').fill('password')
    await page.getByRole('button', { name: 'Sign in' }).click()
    await page.waitForURL('/settings')
    await expect(page).toHaveURL('/settings')
  })
})

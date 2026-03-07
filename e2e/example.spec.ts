import { test, expect } from '@playwright/test';

test('EN landing page loads and has key elements', async ({ page }) => {
  await page.goto('/');
  await expect(page).toHaveTitle(/Apex Talent/i);
  await expect(page.locator('body')).toContainText('Apply Now');
});

test('RU landing page loads and has key elements', async ({ page }) => {
  await page.goto('/ru/');
  await expect(page).toHaveTitle(/Apex Talent/i);
});

import { test, expect } from '@playwright/test';

test.describe('Login Flow', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to login page
    await page.goto('/login');
  });

  test('should display login form', async ({ page }) => {
    // Check if login form elements are present
    await expect(page.getByRole('heading', { name: /sign in/i })).toBeVisible();
    await expect(page.getByLabel(/email/i)).toBeVisible();
    await expect(page.getByLabel(/password/i)).toBeVisible();
    await expect(page.getByRole('button', { name: /sign in/i })).toBeVisible();
    
    // Check for social login buttons
    await expect(page.getByRole('button', { name: /google/i })).toBeVisible();
    await expect(page.getByRole('button', { name: /github/i })).toBeVisible();
  });

  test('should show validation errors for empty fields', async ({ page }) => {
    // Click sign in without filling fields
    await page.getByRole('button', { name: /sign in/i }).click();
    
    // Check for validation messages
    await expect(page.getByText(/email is required/i)).toBeVisible();
    await expect(page.getByText(/password is required/i)).toBeVisible();
  });

  test('should show error for invalid email format', async ({ page }) => {
    // Enter invalid email
    await page.getByLabel(/email/i).fill('invalid-email');
    await page.getByLabel(/password/i).fill('password123');
    await page.getByRole('button', { name: /sign in/i }).click();
    
    // Check for email validation error
    await expect(page.getByText(/invalid email/i)).toBeVisible();
  });

  test('should show error for incorrect credentials', async ({ page }) => {
    // Enter incorrect credentials
    await page.getByLabel(/email/i).fill('test@example.com');
    await page.getByLabel(/password/i).fill('wrongpassword');
    await page.getByRole('button', { name: /sign in/i }).click();
    
    // Wait for error message
    await expect(page.getByText(/invalid email or password/i)).toBeVisible();
  });

  test('should navigate to forgot password page', async ({ page }) => {
    // Click forgot password link
    await page.getByRole('link', { name: /forgot password/i }).click();
    
    // Check if navigated to forgot password page
    await expect(page).toHaveURL('/forgot-password');
    await expect(page.getByRole('heading', { name: /reset password/i })).toBeVisible();
  });

  test('should navigate to signup page', async ({ page }) => {
    // Click sign up link
    await page.getByRole('link', { name: /sign up/i }).click();
    
    // Check if navigated to signup page
    await expect(page).toHaveURL('/signup');
    await expect(page.getByRole('heading', { name: /create.*account/i })).toBeVisible();
  });

  test('should redirect to dashboard after successful login', async ({ page }) => {
    // Mock successful authentication
    await page.route('**/api/auth/login', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          user: {
            uid: 'test-user-id',
            email: 'test@example.com',
            workspaces: ['workspace-1']
          }
        })
      });
    });

    // Fill in login form
    await page.getByLabel(/email/i).fill('test@example.com');
    await page.getByLabel(/password/i).fill('correctpassword');
    
    // Submit form
    await page.getByRole('button', { name: /sign in/i }).click();
    
    // Should redirect to workspace dashboard
    await expect(page).toHaveURL(/\/workspace\/.*\/dashboard/);
  });

  test('should handle loading state during login', async ({ page }) => {
    // Slow down the API response
    await page.route('**/api/auth/login', async route => {
      await new Promise(resolve => setTimeout(resolve, 2000));
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ success: true })
      });
    });

    // Fill in login form
    await page.getByLabel(/email/i).fill('test@example.com');
    await page.getByLabel(/password/i).fill('password123');
    
    // Submit form
    await page.getByRole('button', { name: /sign in/i }).click();
    
    // Check for loading state
    await expect(page.getByRole('button', { name: /signing in/i })).toBeVisible();
    await expect(page.getByRole('button', { name: /signing in/i })).toBeDisabled();
  });

  test('should persist login state across page refreshes', async ({ page, context }) => {
    // Mock successful authentication
    await page.route('**/api/auth/login', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          user: {
            uid: 'test-user-id',
            email: 'test@example.com'
          }
        })
      });
    });

    // Login
    await page.getByLabel(/email/i).fill('test@example.com');
    await page.getByLabel(/password/i).fill('password123');
    await page.getByRole('button', { name: /sign in/i }).click();
    
    // Wait for redirect
    await page.waitForURL(/\/workspace/);
    
    // Refresh page
    await page.reload();
    
    // Should still be on workspace page (not redirected to login)
    await expect(page).toHaveURL(/\/workspace/);
  });
});
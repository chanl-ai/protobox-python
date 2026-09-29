import { test, expect } from '@playwright/test'

test.describe('Workflow Management', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to actions page
    await page.goto('/dashboard/actions')
  })

  test('should display WORKFLOW as an action type option', async ({ page }) => {
    // Click create action button
    await page.click('button:has-text("Create Action")')
    
    // Check that WORKFLOW type is available
    await expect(page.locator('text=Workflow')).toBeVisible()
    await expect(page.locator('text=Create multi-step automated workflows')).toBeVisible()
  })

  test('should create workflow action and redirect to workflow edit page', async ({ page }) => {
    // Click create action button
    await page.click('button:has-text("Create Action")')
    
    // Fill in basic workflow details
    await page.fill('input[placeholder="Action name"]', 'Test Workflow')
    await page.fill('textarea[placeholder="Action description"]', 'A test workflow for automation')
    
    // Select WORKFLOW type
    await page.click('text=Workflow')
    
    // Fill in version
    await page.fill('input[placeholder="1.0.0"]', '1.0.0')
    
    // Fill in tags
    await page.fill('input[placeholder="api, external, production"]', 'automation, test')
    
    // Submit the form
    await page.click('button:has-text("Create Action")')
    
    // Should redirect to workflow edit page
    await expect(page).toHaveURL(/\/dashboard\/actions\/.*\/edit\/workflow/)
    
    // Should show workflow edit page content
    await expect(page.locator('h1:has-text("Edit Workflow")')).toBeVisible()
    await expect(page.locator('text=Workflow Builder Coming Soon')).toBeVisible()
  })

  test('should show workflow icon and label in actions list', async ({ page }) => {
    // Create a workflow action first
    await page.click('button:has-text("Create Action")')
    await page.fill('input[placeholder="Action name"]', 'Test Workflow')
    await page.fill('textarea[placeholder="Action description"]', 'A test workflow')
    await page.click('text=Workflow')
    await page.fill('input[placeholder="1.0.0"]', '1.0.0')
    await page.click('button:has-text("Create Action")')
    
    // Go back to actions list
    await page.goto('/dashboard/actions')
    
    // Should show workflow with correct icon and type
    await expect(page.locator('text=Test Workflow')).toBeVisible()
    await expect(page.locator('text=Workflow')).toBeVisible()
  })

  test('should handle workflow action editing correctly', async ({ page }) => {
    // Create a workflow action first
    await page.click('button:has-text("Create Action")')
    await page.fill('input[placeholder="Action name"]', 'Editable Workflow')
    await page.fill('textarea[placeholder="Action description"]', 'A workflow to edit')
    await page.click('text=Workflow')
    await page.fill('input[placeholder="1.0.0"]', '1.0.0')
    await page.click('button:has-text("Create Action")')
    
    // Should be on workflow edit page
    await expect(page.locator('h1:has-text("Edit Workflow")')).toBeVisible()
    
    // Should be able to edit basic information
    await page.fill('input[placeholder="e.g., Daily Data Sync"]', 'Updated Workflow Name')
    await page.fill('textarea[placeholder="Automatically sync data from external sources and generate daily reports"]', 'Updated workflow description')
    
    // Save changes
    await page.click('button:has-text("Save Workflow")')
    
    // Should show success message
    await expect(page.locator('text=Workflow updated successfully')).toBeVisible()
  })
})

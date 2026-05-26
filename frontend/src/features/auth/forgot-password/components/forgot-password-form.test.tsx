import { beforeEach, describe, expect, it, vi } from 'vitest'
import { render, type RenderResult } from 'vitest-browser-react'
import { userEvent, type Locator } from 'vitest/browser'
import { ForgotPasswordForm } from './forgot-password-form'

const navigateMock = vi.fn()
const requestPasswordResetMock = vi.fn(() =>
  Promise.resolve({ request_id: 'reset-1', delivery: 'local-demo', code: '123456', expires_at: Date.now() })
)

vi.mock('@tanstack/react-router', async (orig) => {
  const actual = await orig<typeof import('@tanstack/react-router')>()
  return { ...actual, useNavigate: () => navigateMock }
})

vi.mock('@/lib/sysml-api', async (orig) => ({
  ...(await orig()),
  requestPasswordReset: requestPasswordResetMock,
}))

describe('ForgotPasswordForm', () => {
  let screen: RenderResult
  let emailInput: Locator
  let continueButton: Locator

  beforeEach(async () => {
    vi.clearAllMocks()

    screen = await render(<ForgotPasswordForm />)
    emailInput = screen.getByRole('textbox', { name: /^Email$/i })
    continueButton = screen.getByRole('button', { name: /^发送验证码$/i })
  })

  it('renders email field and continue button', async () => {
    await expect.element(emailInput).toBeInTheDocument()
    await expect.element(continueButton).toBeInTheDocument()
  })

  it('shows validation when submitting empty form', async () => {
    await userEvent.click(continueButton)
    await expect
      .element(screen.getByText(/^请输入邮箱。$/i))
      .toBeInTheDocument()
  })

  it('requests reset and navigates to /otp on success', async () => {
    await userEvent.fill(emailInput, 'a@b.com')
    await userEvent.click(continueButton)

    await vi.waitFor(() =>
      expect(requestPasswordResetMock).toHaveBeenCalledWith('a@b.com')
    )
    await vi.waitFor(() =>
      expect(navigateMock).toHaveBeenCalledWith({
        to: '/otp',
        search: { requestId: 'reset-1', email: 'a@b.com' },
      })
    )

    // Form should reset on success
    await expect.element(emailInput).toHaveValue('')
  })
})

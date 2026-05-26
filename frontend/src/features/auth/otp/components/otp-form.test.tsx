import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { render, type RenderResult } from 'vitest-browser-react'
import { type Locator, userEvent } from 'vitest/browser'
import { OtpForm } from './otp-form'

const navigate = vi.fn()
const verifyPasswordResetCodeMock = vi.fn(() =>
  Promise.resolve({ request_id: 'reset-1', username: 'engineer', verified: true })
)
const setNewPasswordMock = vi.fn(() =>
  Promise.resolve({ username: 'engineer', reset: true })
)

vi.mock('@tanstack/react-router', async (orig) => {
  const actual = await orig<typeof import('@tanstack/react-router')>()
  return {
    ...actual,
    useNavigate: () => navigate,
    useSearch: () => ({ requestId: 'reset-1', email: 'engineer@example.com' }),
  }
})

vi.mock('@/lib/sysml-api', async (orig) => ({
  ...(await orig()),
  verifyPasswordResetCode: verifyPasswordResetCodeMock,
  setNewPassword: setNewPasswordMock,
}))

describe('OtpForm', () => {
  let screen: RenderResult
  let otpInput: Locator
  let verifyButton: Locator

  beforeEach(async () => {
    vi.clearAllMocks()

    screen = await render(<OtpForm />)
    otpInput = screen.getByLabelText(/^One-Time Password$/i)
    verifyButton = screen.getByRole('button', { name: /^验证验证码$/i })
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('disables Verify until 6 digits are entered', async () => {
    await expect.element(verifyButton).toBeDisabled()

    await userEvent.fill(otpInput, '12345')
    await expect.element(verifyButton).toBeDisabled()

    await userEvent.fill(otpInput, '123456')
    await expect.element(verifyButton).toBeEnabled()
  })

  it('submits the OTP and navigates after timeout', async () => {
    await userEvent.fill(otpInput, '123456')
    await userEvent.click(verifyButton)

    await vi.waitFor(() =>
      expect(verifyPasswordResetCodeMock).toHaveBeenCalledWith('reset-1', '123456')
    )
    await expect.element(screen.getByRole('button', { name: /^更新密码$/i })).toBeInTheDocument()

    await userEvent.fill(screen.getByLabelText(/^New Password$/i), 'newpass123')
    await userEvent.click(screen.getByRole('button', { name: /^更新密码$/i }))

    await vi.waitFor(() =>
      expect(setNewPasswordMock).toHaveBeenCalledWith('reset-1', 'newpass123')
    )
    await vi.waitFor(() =>
      expect(navigate).toHaveBeenCalledWith({ to: '/sign-in', replace: true })
    )
  })
})

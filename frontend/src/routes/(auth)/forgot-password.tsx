import { createFileRoute } from '@tanstack/react-router'
import { z } from 'zod'
import { ForgotPassword } from '@/features/auth/forgot-password'

const searchSchema = z.object({
  email: z.string().optional(),
  requestId: z.string().optional(),
})

export const Route = createFileRoute('/(auth)/forgot-password')({
  component: ForgotPassword,
  validateSearch: searchSchema,
})

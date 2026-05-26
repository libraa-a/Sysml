import { createFileRoute } from '@tanstack/react-router'
import { z } from 'zod'
import { Otp } from '@/features/auth/otp'

const searchSchema = z.object({
  requestId: z.string().optional(),
  email: z.string().optional(),
})

export const Route = createFileRoute('/(auth)/otp')({
  component: Otp,
  validateSearch: searchSchema,
})

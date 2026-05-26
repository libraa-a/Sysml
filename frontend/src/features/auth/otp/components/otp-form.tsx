import { useState } from 'react'
import { z } from 'zod'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { useNavigate, useSearch } from '@tanstack/react-router'
import { toast } from 'sonner'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { setNewPassword, verifyPasswordResetCode } from '@/lib/sysml-api'
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from '@/components/ui/form'
import {
  InputOTP,
  InputOTPGroup,
  InputOTPSlot,
  InputOTPSeparator,
} from '@/components/ui/input-otp'
import { Input } from '@/components/ui/input'

const formSchema = z.object({
  otp: z.string().length(6, '请输入 6 位验证码。'),
  password: z.string().min(7, '密码至少需要 7 位。'),
})

type OtpFormProps = React.HTMLAttributes<HTMLFormElement>

export function OtpForm({ className, ...props }: OtpFormProps) {
  const navigate = useNavigate()
  const { requestId, email } = useSearch({ from: '/(auth)/otp' })
  const [isLoading, setIsLoading] = useState(false)
  const [verified, setVerified] = useState(false)

  const form = useForm<z.infer<typeof formSchema>>({
    resolver: zodResolver(formSchema),
    defaultValues: { otp: '', password: '' },
  })

  // eslint-disable-next-line react-hooks/incompatible-library
  const otp = form.watch('otp')

  async function onSubmit(data: z.infer<typeof formSchema>) {
    setIsLoading(true)
    try {
      if (!verified) {
        await verifyPasswordResetCode(requestId || '', data.otp)
        setVerified(true)
        toast.success('验证码验证成功，请设置新密码。')
      } else {
        await setNewPassword(requestId || '', data.password)
        toast.success('密码已重置，请重新登录。')
        navigate({ to: '/sign-in', replace: true })
      }
    } catch (error) {
      toast.error(error instanceof Error ? error.message : '验证失败')
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <Form {...form}>
      <form
        onSubmit={form.handleSubmit(onSubmit)}
        className={cn('grid gap-2', className)}
        {...props}
      >
        <div className='rounded-md border bg-muted/30 px-3 py-2 text-sm text-muted-foreground'>
          {email ? `验证码已发送到 ${email}` : '请先输入验证码，再设置新密码。'}
        </div>
        <FormField
          control={form.control}
          name='otp'
          render={({ field }) => (
            <FormItem>
              <FormLabel className='sr-only'>One-Time Password</FormLabel>
              <FormControl>
                <InputOTP
                  maxLength={6}
                  {...field}
                  containerClassName='justify-between sm:[&>[data-slot="input-otp-group"]>div]:w-12'
                >
                  <InputOTPGroup>
                    <InputOTPSlot index={0} />
                    <InputOTPSlot index={1} />
                  </InputOTPGroup>
                  <InputOTPSeparator />
                  <InputOTPGroup>
                    <InputOTPSlot index={2} />
                    <InputOTPSlot index={3} />
                  </InputOTPGroup>
                  <InputOTPSeparator />
                  <InputOTPGroup>
                    <InputOTPSlot index={4} />
                    <InputOTPSlot index={5} />
                  </InputOTPGroup>
                </InputOTP>
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />
        {verified ? (
          <FormField
            control={form.control}
            name='password'
            render={({ field }) => (
              <FormItem>
                <FormLabel>New Password</FormLabel>
                <FormControl>
                  <Input type='password' placeholder='输入新密码' {...field} />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
        ) : null}
        <Button className='mt-2' disabled={(!verified && otp.length < 6) || isLoading}>
          {verified ? '更新密码' : '验证验证码'}
        </Button>
      </form>
    </Form>
  )
}

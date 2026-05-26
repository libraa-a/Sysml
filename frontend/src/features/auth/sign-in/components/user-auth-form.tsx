import { useState } from 'react'
import { z } from 'zod'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { Link, useNavigate } from '@tanstack/react-router'
import { AlertCircle, Loader2, LogIn } from 'lucide-react'
import { toast } from 'sonner'
import { useAuthStore } from '@/stores/auth-store'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { login, saveIdentity } from '@/lib/sysml-api'
import { Alert, AlertDescription } from '@/components/ui/alert'
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from '@/components/ui/form'
import { Input } from '@/components/ui/input'
import { PasswordInput } from '@/components/password-input'

const formSchema = z.object({
  username: z
    .string()
    .trim()
    .min(1, '请输入用户名。')
    .regex(/^[A-Za-z0-9_-]{3,30}$/, '用户名需为 3-30 位字母、数字、下划线或连字符。'),
  password: z
    .string()
    .min(1, '请输入密码。')
    .min(7, '密码至少需要 7 位。'),
})

interface UserAuthFormProps extends React.HTMLAttributes<HTMLFormElement> {}

export function UserAuthForm({ className, ...props }: UserAuthFormProps) {
  const [isLoading, setIsLoading] = useState(false)
  const [serverError, setServerError] = useState('')
  const navigate = useNavigate()
  const { auth } = useAuthStore()

  const form = useForm<z.infer<typeof formSchema>>({
    resolver: zodResolver(formSchema),
    defaultValues: {
      username: '',
      password: '',
    },
  })

  async function onSubmit(data: z.infer<typeof formSchema>) {
    setIsLoading(true)
    setServerError('')

    try {
      const payload = await login(data.username.trim(), data.password)
      const identity = payload.identity
      saveIdentity(identity)
      auth.setUser({
        accountNo: 'ACC001',
        email: identity.username,
        role: [identity.role],
        exp: identity.exp ?? Date.now(),
      })
      auth.setAccessToken(identity.token ?? '')

      navigate({ to: '/', replace: true })
      toast.success(`欢迎回来：${identity.display || identity.username}`)
    } catch (error) {
      const message = error instanceof Error ? error.message : '登录失败'
      setServerError(message)
      toast.error(message)
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <Form {...form}>
      <form
        onSubmit={form.handleSubmit(onSubmit)}
        className={cn('grid gap-3', className)}
        {...props}
      >
        {serverError ? (
          <Alert variant='destructive'>
            <AlertCircle />
            <AlertDescription>{serverError}</AlertDescription>
          </Alert>
        ) : null}
        <FormField
          control={form.control}
          name='username'
          render={({ field }) => (
            <FormItem>
              <FormLabel>Username</FormLabel>
              <FormControl>
                <Input
                  autoComplete='username'
                  placeholder='请输入用户名'
                  {...field}
                />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />
        <FormField
          control={form.control}
          name='password'
          render={({ field }) => (
            <FormItem className='relative'>
              <FormLabel>Password</FormLabel>
              <FormControl>
                <PasswordInput
                  autoComplete='current-password'
                  placeholder='请输入密码'
                  {...field}
                />
              </FormControl>
              <FormMessage />
              <Link
                to='/forgot-password'
                className='absolute inset-e-0 -top-0.5 text-sm font-medium text-muted-foreground hover:opacity-75'
              >
                忘记密码？
              </Link>
            </FormItem>
          )}
        />
        <Button type='submit' className='mt-2' disabled={isLoading}>
          {isLoading ? <Loader2 className='animate-spin' /> : <LogIn />}
          登录
        </Button>
        <Button variant='outline' className='w-full' asChild>
          <Link to='/sign-up'>注册</Link>
        </Button>
      </form>
    </Form>
  )
}

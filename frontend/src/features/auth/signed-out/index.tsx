import { Link } from '@tanstack/react-router'
import { LogIn, ShieldCheck } from 'lucide-react'
import { AuthLayout } from '../auth-layout'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'

export function SignedOut() {
  return (
    <AuthLayout>
      <Card className='max-w-md gap-4'>
        <CardHeader>
          <CardTitle className='text-lg tracking-tight'>You are signed out</CardTitle>
          <CardDescription>
            Your session has been cleared. You can sign in again when you need access.
          </CardDescription>
        </CardHeader>
        <CardContent className='flex flex-col gap-3'>
          <div className='flex items-center gap-2 rounded-md border bg-muted/40 px-3 py-2 text-sm text-muted-foreground'>
            <ShieldCheck className='size-4 text-primary' />
            Session closed successfully
          </div>
          <Button asChild>
            <Link to='/sign-in'>
              <LogIn />
              Sign in again
            </Link>
          </Button>
        </CardContent>
      </Card>
    </AuthLayout>
  )
}

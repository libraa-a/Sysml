import { useEffect } from 'react'
import { useNavigate } from '@tanstack/react-router'
import { loadIdentity } from '@/lib/sysml-api'
import { SysmlWorkbench } from '@/features/sysml-workbench'

export function Dashboard() {
  const navigate = useNavigate()

  useEffect(() => {
    if (!loadIdentity()) {
      navigate({ to: '/sign-in', replace: true })
    }
  }, [navigate])

  return <SysmlWorkbench />
}

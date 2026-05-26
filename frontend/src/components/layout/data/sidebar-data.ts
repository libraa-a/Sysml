import {
  Archive,
  Boxes,
  Braces,
  Eye,
  FileText,
  GitBranch,
  LayoutDashboard,
  MessageCircle,
  Network,
  Wrench,
  Workflow,
} from 'lucide-react'
import { type SidebarData } from '../types'

export const sidebarData: SidebarData = {
  user: {
    name: 'engineer',
    email: 'engineer / author',
    avatar: '',
  },
  teams: [
    {
      name: 'MBSE Workspace',
      logo: Braces,
      plan: 'Projects / Models / Docs',
    },
    {
      name: 'Project Workspace',
      logo: Boxes,
      plan: 'Model / Trace / Version',
    },
    {
      name: 'External Tools',
      logo: Archive,
      plan: 'Cameo / XMI / MDK',
    },
  ],
  navGroups: [
    {
      title: 'Portfolio',
      items: [
        {
          title: 'Overview',
          url: '/#overview',
          icon: LayoutDashboard,
        },
        {
          title: 'Projects',
          url: '/#projects',
          icon: Boxes,
        },
        {
          title: 'Workspace',
          url: '/#workspace',
          icon: Braces,
        },
      ],
    },
    {
      title: 'Project Workspace',
      items: [
        {
          title: 'Model',
          url: '/#model',
          icon: Archive,
        },
        {
          title: 'Views',
          url: '/#views',
          icon: Eye,
        },
        {
          title: 'Graph',
          url: '/#diagram',
          icon: Network,
        },
        {
          title: 'Trace',
          url: '/#trace',
          icon: Workflow,
        },
        {
          title: 'Versions',
          url: '/#version',
          icon: GitBranch,
        },
        {
          title: 'Docs',
          url: '/#docgen',
          icon: FileText,
        },
        {
          title: 'MDK',
          url: '/#mdk',
          icon: Wrench,
        },
        {
          title: 'Assistant',
          url: '/#assistant',
          icon: MessageCircle,
        },
      ],
    },
  ],
}

import {
  Archive,
  BookOpenText,
  Boxes,
  Braces,
  ChartNoAxesCombined,
  FileText,
  GitBranch,
  LayoutDashboard,
  Network,
  NotebookTabs,
  ShieldCheck,
  Wrench,
  Waypoints,
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
      name: 'SysML DocGen',
      logo: Braces,
      plan: 'MMS / VE / MDK / DocGen',
    },
    {
      name: 'Satellite Power',
      logo: Boxes,
      plan: 'Sample project',
    },
    {
      name: 'FastAPI Backend',
      logo: Archive,
      plan: 'Local API',
    },
  ],
  navGroups: [
    {
      title: 'Workbench',
      items: [
        {
          title: 'Overview',
          url: '/#model',
          icon: LayoutDashboard,
        },
        {
          title: 'Workflow',
          icon: Workflow,
          items: [
            {
              title: 'MMS Models',
              url: '/#model',
              icon: Boxes,
            },
            {
              title: 'VE Graph',
              url: '/#diagram',
              icon: Network,
            },
            {
              title: 'Trace Matrix',
              url: '/#trace',
              icon: Workflow,
            },
            {
              title: 'Versions',
              url: '/#version',
              icon: GitBranch,
            },
            {
              title: 'DocGen Docs',
              url: '/#docgen',
              icon: FileText,
            },
            {
              title: 'MDK',
              url: '/#mdk',
              icon: Wrench,
            },
          ],
        },
      ],
    },
    {
      title: 'Reference',
      items: [
        {
          title: 'API & Docs',
          icon: ShieldCheck,
          items: [
            {
              title: 'OpenAPI',
              url: '/docs',
              icon: NotebookTabs,
            },
            {
              title: 'API Guide',
              url: '/api.md',
              icon: BookOpenText,
            },
            {
              title: 'MDK Guide',
              url: '/mdk.md',
              icon: Waypoints,
            },
          ],
        },
        {
          title: 'Template Pages',
          icon: ChartNoAxesCombined,
          items: [
            {
              title: 'Tasks',
              url: '/tasks',
            },
            {
              title: 'Users',
              url: '/users',
            },
            {
              title: 'Apps',
              url: '/apps',
            },
          ],
        },
      ],
    },
  ],
}

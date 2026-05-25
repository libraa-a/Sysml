import {
  Archive,
  BookOpenText,
  Boxes,
  Braces,
  ChartNoAxesCombined,
  Eye,
  FileText,
  GitBranch,
  LayoutDashboard,
  MessageCircle,
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
      plan: 'Projects / Views / Docs',
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
          url: '/#overview',
          icon: LayoutDashboard,
        },
        {
          title: 'Projects',
          url: '/#projects',
          icon: Boxes,
        },
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

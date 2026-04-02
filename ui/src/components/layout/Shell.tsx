import { Outlet } from 'react-router-dom'
import TopNav from './TopNav'

export default function Shell() {
  return (
    <div className="flex flex-col w-full min-h-screen">
      <TopNav />
      <main className="flex-1 overflow-hidden">
        <Outlet />
      </main>
    </div>
  )
}

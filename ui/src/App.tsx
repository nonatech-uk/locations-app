import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import Shell from './components/layout/Shell'
import Explorer from './pages/Explorer'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Shell />}>
          <Route path="/explorer" element={<Explorer />} />
          <Route path="*" element={<Navigate to="/explorer" replace />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}

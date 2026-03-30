import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import Shell from './components/layout/Shell'
import Explorer from './pages/Explorer'
import Flights from './pages/Flights'
import GAFlights from './pages/GAFlights'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Shell />}>
          <Route path="/explorer" element={<Explorer />} />
          <Route path="/flights" element={<Flights />} />
          <Route path="/ga" element={<GAFlights />} />
          <Route path="*" element={<Navigate to="/explorer" replace />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}

import { BrowserRouter as Router, Routes, Route } from "react-router-dom"
import Home from "./pages/Home"
import Dashboard from "./pages/Dashboard"
import Architecture from "./pages/Architecture"
import About from "./pages/About"

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/architecture" element={<Architecture />} />
        <Route path="/about" element={<About />} />
      </Routes>
    </Router>
  )
}

export default App

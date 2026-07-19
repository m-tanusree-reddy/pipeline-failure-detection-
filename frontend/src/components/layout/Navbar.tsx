import { Link } from "react-router-dom"
import { motion } from "framer-motion"

export default function Navbar() {
  return (
    <header className="fixed top-0 w-full z-50 bg-background/60 backdrop-blur-md border-b border-white/10 shadow-sm">
      <div className="flex justify-between items-center h-16 px-6 max-w-[1440px] mx-auto">
        <div className="flex items-center gap-4">
          <Link to="/" className="font-sans text-2xl font-bold text-foreground">
            CI Debug Agent
          </Link>
        </div>
        
        <nav className="hidden md:flex items-center gap-6">
          <Link to="/" className="text-primary font-bold border-b-2 border-primary pb-1 font-sans text-base">
            Home
          </Link>
          <Link to="/architecture" className="text-muted-foreground hover:text-foreground transition-colors font-sans text-base">
            Architecture
          </Link>
          <Link to="/about" className="text-muted-foreground hover:text-foreground transition-colors font-sans text-base">
            About
          </Link>
          <Link to="/dashboard" className="text-muted-foreground hover:text-foreground transition-colors font-sans text-base">
            Dashboard
          </Link>
        </nav>
        
        <div className="flex items-center gap-4">
          <motion.button 
            whileHover={{ scale: 1.05, opacity: 0.9 }}
            whileTap={{ scale: 0.95 }}
            className="bg-primary text-primary-foreground font-bold py-2 px-6 rounded-full transition-all text-sm font-sans"
          >
            GitHub
          </motion.button>
        </div>
      </div>
    </header>
  )
}

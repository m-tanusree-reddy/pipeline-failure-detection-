import Navbar from "../components/layout/Navbar"
import Footer from "../components/layout/Footer"
import Hero from "../components/home/Hero"
import Stats from "../components/home/Stats"
import Features from "../components/home/Features"
import CTA from "../components/home/CTA"

export default function Home() {
  return (
    <div className="min-h-screen flex flex-col">
      <Navbar />
      <main className="flex-grow">
        <Hero />
        <Stats />
        <Features />
        <CTA />
      </main>
      <Footer />
    </div>
  )
}

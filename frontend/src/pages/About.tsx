import Navbar from "../components/layout/Navbar"
import Footer from "../components/layout/Footer"
import { Shield, Zap, Users } from "lucide-react"

export default function About() {
  return (
    <div className="min-h-screen flex flex-col bg-background text-foreground">
      <Navbar />
      
      <main className="flex-grow pt-24 pb-16 px-6 max-w-[1440px] mx-auto w-full animate-in fade-in slide-in-from-bottom-4 duration-700">
        <div className="max-w-3xl mx-auto text-center mb-16">
          <h1 className="font-sans text-5xl font-bold text-foreground mb-6">About CI Debug Agent</h1>
          <p className="font-sans text-lg text-muted-foreground">
            We are building the future of autonomous site reliability engineering. Our mission is to eliminate the hours engineers spend digging through cryptic CI/CD logs, allowing them to focus on building great products.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-8 mb-16">
          <div className="bg-card/60 backdrop-blur-md p-8 rounded-2xl border border-white/10 text-center flex flex-col items-center">
            <div className="w-16 h-16 rounded-full bg-primary/10 flex items-center justify-center text-primary mb-6">
              <Zap className="w-8 h-8" />
            </div>
            <h3 className="font-sans text-xl font-bold text-foreground mb-4">Speed</h3>
            <p className="font-sans text-sm text-muted-foreground">
              What used to take hours of manual log parsing now takes milliseconds. Our vector search engine identifies failure patterns instantly.
            </p>
          </div>
          
          <div className="bg-card/60 backdrop-blur-md p-8 rounded-2xl border border-white/10 text-center flex flex-col items-center">
            <div className="w-16 h-16 rounded-full bg-primary/10 flex items-center justify-center text-primary mb-6">
              <Shield className="w-8 h-8" />
            </div>
            <h3 className="font-sans text-xl font-bold text-foreground mb-4">Accuracy</h3>
            <p className="font-sans text-sm text-muted-foreground">
              By utilizing a multi-agent architecture with a dedicated Critic agent, we ensure our root cause analyses are robust, verified, and hallucination-free.
            </p>
          </div>
          
          <div className="bg-card/60 backdrop-blur-md p-8 rounded-2xl border border-white/10 text-center flex flex-col items-center">
            <div className="w-16 h-16 rounded-full bg-primary/10 flex items-center justify-center text-primary mb-6">
              <Users className="w-8 h-8" />
            </div>
            <h3 className="font-sans text-xl font-bold text-foreground mb-4">Developer Experience</h3>
            <p className="font-sans text-sm text-muted-foreground">
              Built by developers for developers. We integrate directly into your workflow, providing actionable fixes right when you need them.
            </p>
          </div>
        </div>
      </main>

      <Footer />
    </div>
  )
}

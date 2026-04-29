"use client";

import { useEffect } from "react";

const PAYMENT = "https://buy.stripe.com/6oU8wQcdKg1pgXg64zePp0x";

/* ─── tiny svg icons ─────────────────────────────────────────── */
function IconUpload() {
  return (
    <svg width="26" height="26" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="1.6">
      <path strokeLinecap="round" strokeLinejoin="round"
        d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5" />
    </svg>
  );
}
function IconFilm() {
  return (
    <svg width="26" height="26" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="1.6">
      <path strokeLinecap="round" strokeLinejoin="round"
        d="M3.375 19.5h17.25m-17.25 0a1.125 1.125 0 01-1.125-1.125M3.375 19.5h1.5C5.496 19.5 6 18.996 6 18.375m-3.75.125v-.094c0-.621.504-1.125 1.125-1.125h1.5m12.75 1.219v-.094c0-.621-.504-1.125-1.125-1.125h-1.5m3.75.219a1.125 1.125 0 001.125-1.125V4.875m-3.75 14.625V18.375c0-.621-.504-1.125-1.125-1.125h-10.5A1.125 1.125 0 005.625 18.375v.125M21 4.875A1.125 1.125 0 0019.875 3.75h-15.75A1.125 1.125 0 003 4.875V18.75M21 4.875v13.875" />
    </svg>
  );
}
function IconBolt() {
  return (
    <svg width="26" height="26" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="1.6">
      <path strokeLinecap="round" strokeLinejoin="round"
        d="M3.75 13.5l10.5-11.25L12 10.5h8.25L9.75 21.75 12 13.5H3.75z" />
    </svg>
  );
}
function IconCheck() {
  return (
    <svg width="14" height="14" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2.5">
      <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
    </svg>
  );
}

/* ─── data ───────────────────────────────────────────────────── */
const valueProps = [
  {
    icon: <IconUpload />,
    tag: "Universal Compatibility",
    title: "Upload Any Data Format",
    desc: "CSV, Excel, Google Sheets — all formats accepted. No reformatting or cleanup required on your end.",
  },
  {
    icon: <IconFilm />,
    tag: "Full-Service Production",
    title: "We Handle Everything",
    desc: "Script, design, animation, narration, and brand integration. You send data — we deliver cinema.",
  },
  {
    icon: <IconBolt />,
    tag: "Fast Turnaround",
    title: "Video Delivered in 48h",
    desc: "A polished MP4 and shareable link in your inbox within 48 hours. Professional, embeddable, brandable.",
  },
];

const steps = [
  {
    num: "01",
    title: "Upload Your Data",
    desc: "Drop your CSV or spreadsheet into our secure portal. We accept Excel, Google Sheets, and raw CSV — all formats welcome.",
  },
  {
    num: "02",
    title: "We Produce Your Video",
    desc: "Our team transforms your data into a compelling visual narrative — motion graphics, voiceover, your brand colors.",
  },
  {
    num: "03",
    title: "Receive & Share",
    desc: "Get a polished MP4 and a shareable link within 48 hours. Ready to embed, present, or distribute.",
  },
];

const plans = [
  {
    tier: "Starter",
    price: "$299",
    cadence: "/ video",
    tagline: "Perfect for one-off reports",
    highlight: false,
    features: [
      "1 video",
      "Up to 500 data rows",
      "HD quality",
      "48h delivery",
      "2 revision rounds",
    ],
    cta: "Get Started",
  },
  {
    tier: "Growth",
    price: "$799",
    cadence: "/ month",
    tagline: "3 videos per month",
    highlight: true,
    features: [
      "3 videos / month",
      "Unlimited rows",
      "HD + 4K quality",
      "Priority 24h delivery",
      "Unlimited revisions",
      "Brand kit included",
    ],
    cta: "Get Started",
  },
  {
    tier: "Enterprise",
    price: "Custom",
    cadence: "",
    tagline: "Volume & custom workflows",
    highlight: false,
    features: [
      "Unlimited videos",
      "API access",
      "Dedicated account manager",
      "White-label option",
      "SLA guarantee",
    ],
    cta: "Contact Us",
  },
];

const logos = ["DataFlow", "MetricsCo", "Insight Labs", "Pulse Analytics", "Vanta"];

const testimonials = [
  {
    quote:
      "Rendara transformed our quarterly reports into video summaries stakeholders actually watch. Engagement went through the roof.",
    name: "Sarah Chen",
    title: "Head of Analytics, DataFlow",
    avatar: "SC",
  },
  {
    quote:
      "We went from 3 days of presentation prep to a polished video in 48 hours. The ROI is undeniable — we use it every month.",
    name: "Marcus Williams",
    title: "VP Strategy, MetricsCo",
    avatar: "MW",
  },
  {
    quote:
      "Indistinguishable from an expensive agency, at a fraction of the cost and with zero back-and-forth.",
    name: "Priya Patel",
    title: "Data Director, Insight Labs",
    avatar: "PP",
  },
];

/* ─── page ───────────────────────────────────────────────────── */
export default function Home() {
  useEffect(() => {
    const els = document.querySelectorAll<HTMLElement>(".reveal");
    const obs = new IntersectionObserver(
      (entries) => {
        entries.forEach((e) => {
          if (e.isIntersecting) {
            e.target.classList.add("visible");
            obs.unobserve(e.target);
          }
        });
      },
      { threshold: 0.08 }
    );
    els.forEach((el) => obs.observe(el));
    return () => obs.disconnect();
  }, []);

  return (
    <div className="min-h-screen bg-[#080810] text-white overflow-x-hidden">

      {/* ── NAVBAR ─────────────────────────────────────────── */}
      <nav
        className="fixed top-0 inset-x-0 z-50"
        style={{
          backdropFilter: "blur(20px)",
          background: "rgba(8,8,16,.85)",
          borderBottom: "1px solid rgba(255,255,255,.06)",
        }}
      >
        <div className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
          <span className="font-data font-semibold text-lg tracking-tight g-text">Rendara</span>
          <a
            href={PAYMENT}
            target="_blank"
            rel="noopener noreferrer"
            className="btn-primary rounded-lg px-5 py-2 text-sm font-semibold text-white"
          >
            Get Started →
          </a>
        </div>
      </nav>

      {/* ── HERO ───────────────────────────────────────────── */}
      <section className="hero-bg dot-grid relative min-h-screen flex flex-col items-center justify-center pt-16 pb-10 px-6">
        {/* decorative glow orbs */}
        <div
          className="absolute pointer-events-none"
          style={{
            top: "22%", left: "12%",
            width: 500, height: 500,
            borderRadius: "50%",
            background: "radial-gradient(circle, rgba(139,92,246,.2) 0%, transparent 70%)",
            filter: "blur(70px)",
            animation: "pulse-ring 7s ease-in-out infinite",
          }}
        />
        <div
          className="absolute pointer-events-none"
          style={{
            bottom: "18%", right: "8%",
            width: 380, height: 380,
            borderRadius: "50%",
            background: "radial-gradient(circle, rgba(59,130,246,.16) 0%, transparent 70%)",
            filter: "blur(70px)",
            animation: "pulse-ring 9s ease-in-out infinite 2.5s",
          }}
        />

        <div className="relative z-10 max-w-4xl mx-auto text-center">
          {/* badge */}
          <div
            className="inline-flex items-center gap-2 rounded-full px-4 py-1.5 mb-8 font-data text-xs tracking-widest text-violet-300"
            style={{ border: "1px solid rgba(139,92,246,.3)", background: "rgba(139,92,246,.08)" }}
          >
            <span
              className="w-1.5 h-1.5 rounded-full bg-violet-400"
              style={{ animation: "pulse-ring 2s ease-in-out infinite" }}
            />
            AUTOMATED VIDEO PRODUCTION
          </div>

          <h1 className="text-5xl sm:text-6xl lg:text-[4.5rem] font-bold tracking-tight leading-[1.05] mb-6">
            Turn Your Data Into{" "}
            <span className="g-text">Compelling Videos</span>
            {" "}— Automatically
          </h1>

          <p className="text-lg sm:text-xl text-slate-400 max-w-2xl mx-auto mb-10 leading-relaxed">
            Send us your CSV or spreadsheet. We deliver a polished, branded video
            ready to share — no design skills required.
          </p>

          <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
            <a
              href={PAYMENT}
              target="_blank"
              rel="noopener noreferrer"
              className="btn-primary rounded-xl px-8 py-4 font-bold text-base text-white"
            >
              Get Your First Video →
            </a>
            <a
              href="#how-it-works"
              className="btn-ghost rounded-xl px-8 py-4 font-medium text-slate-300 text-base"
            >
              See How It Works
            </a>
          </div>

          {/* stats */}
          <div className="mt-20 flex flex-col sm:flex-row items-center justify-center gap-10 sm:gap-20">
            {[
              ["200+", "Teams Served"],
              ["48h", "Avg. Delivery"],
              ["4.9★", "Client Rating"],
            ].map(([val, label]) => (
              <div key={label} className="text-center">
                <div className="text-3xl font-bold g-text">{val}</div>
                <div className="text-sm text-slate-500 mt-1 font-data tracking-wide">{label}</div>
              </div>
            ))}
          </div>
        </div>

        {/* scroll hint */}
        <div className="absolute bottom-8 left-1/2 -translate-x-1/2 flex flex-col items-center gap-2 opacity-25 pointer-events-none">
          <span className="font-data text-[10px] tracking-widest text-slate-500">SCROLL</span>
          <div
            className="w-px h-8"
            style={{ background: "linear-gradient(to bottom, rgba(139,92,246,.6), transparent)" }}
          />
        </div>
      </section>

      {/* ── VALUE PROPS ────────────────────────────────────── */}
      <section className="py-24 bg-[#0b0b16]">
        <div className="max-w-6xl mx-auto px-6">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
            {valueProps.map((v, i) => (
              <div
                key={v.title}
                className="card card-beam reveal p-8"
                style={{ transitionDelay: `${i * 0.12}s` }}
              >
                <div
                  className="text-violet-400 mb-5 w-10 h-10 flex items-center justify-center rounded-lg shrink-0"
                  style={{ background: "rgba(139,92,246,.1)", border: "1px solid rgba(139,92,246,.2)" }}
                >
                  {v.icon}
                </div>
                <div className="font-data text-[10px] text-violet-500 tracking-widest mb-3 uppercase">
                  {v.tag}
                </div>
                <h3 className="text-lg font-bold mb-3 text-white">{v.title}</h3>
                <p className="text-slate-400 text-sm leading-relaxed">{v.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── HOW IT WORKS ───────────────────────────────────── */}
      <section id="how-it-works" className="py-32 bg-[#080810] line-grid relative">
        <div className="max-w-6xl mx-auto px-6">
          <div className="text-center mb-20 reveal">
            <div className="font-data text-[10px] text-violet-500 tracking-widest mb-4 uppercase">Process</div>
            <h2 className="text-4xl sm:text-5xl font-bold tracking-tight">How It Works</h2>
            <p className="text-slate-400 mt-4 max-w-md mx-auto">
              From raw data to polished video in three simple steps
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-12 relative">
            {/* connector line */}
            <div
              className="hidden md:block absolute"
              style={{
                top: 56,
                left: "calc(16.67% + 2.5rem)",
                right: "calc(16.67% + 2.5rem)",
                height: 1,
                background: "linear-gradient(90deg, rgba(139,92,246,.5), rgba(59,130,246,.5), rgba(139,92,246,.5))",
              }}
            />

            {steps.map((step, i) => (
              <div
                key={step.num}
                className="reveal text-center flex flex-col items-center"
                style={{ transitionDelay: `${i * 0.15}s` }}
              >
                <div
                  className="relative flex items-center justify-center w-28 h-28 rounded-2xl mb-8"
                  style={{
                    background: "rgba(139,92,246,.08)",
                    border: "1px solid rgba(139,92,246,.25)",
                    boxShadow: "0 0 40px rgba(139,92,246,.1)",
                  }}
                >
                  <span className="font-data font-bold text-3xl g-text">{step.num}</span>
                </div>
                <h3 className="text-xl font-bold mb-4">{step.title}</h3>
                <p className="text-slate-400 text-sm leading-relaxed max-w-xs">{step.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── PRICING ────────────────────────────────────────── */}
      <section className="py-32 bg-[#0b0b16]">
        <div className="max-w-6xl mx-auto px-6">
          <div className="text-center mb-20 reveal">
            <div className="font-data text-[10px] text-violet-500 tracking-widest mb-4 uppercase">Pricing</div>
            <h2 className="text-4xl sm:text-5xl font-bold tracking-tight">
              Simple, Transparent Pricing
            </h2>
            <p className="text-slate-400 mt-4">No hidden fees. Pay only for what you need.</p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 items-start">
            {plans.map((plan, i) => (
              <div
                key={plan.tier}
                className={`reveal relative p-8 rounded-2xl ${plan.highlight ? "" : "card"}`}
                style={
                  plan.highlight
                    ? {
                        background:
                          "linear-gradient(160deg, rgba(109,40,217,.18) 0%, rgba(37,99,235,.12) 100%)",
                        border: "1px solid rgba(139,92,246,.45)",
                        boxShadow: "0 0 60px rgba(139,92,246,.18)",
                        transform: "scale(1.03)",
                        transitionDelay: `${i * 0.1}s`,
                      }
                    : { transitionDelay: `${i * 0.1}s` }
                }
              >
                {plan.highlight && (
                  <div
                    className="absolute -top-4 left-1/2 -translate-x-1/2 px-4 py-1 rounded-full text-xs font-bold whitespace-nowrap"
                    style={{ background: "linear-gradient(135deg, #7c3aed 0%, #2563eb 100%)" }}
                  >
                    ✦ Most Popular
                  </div>
                )}

                <div
                  className="font-data text-[10px] tracking-widest mb-4 uppercase"
                  style={{ color: plan.highlight ? "#a78bfa" : "#64748b" }}
                >
                  {plan.tier}
                </div>

                <div className="flex items-end gap-1 mb-1">
                  <span className="text-4xl font-bold">{plan.price}</span>
                  {plan.cadence && (
                    <span className="text-slate-400 mb-1 text-sm">{plan.cadence}</span>
                  )}
                </div>
                <p className="text-slate-500 text-sm mb-8">{plan.tagline}</p>

                <ul className="space-y-3 mb-8">
                  {plan.features.map((f) => (
                    <li key={f} className="flex items-center gap-3 text-sm text-slate-300">
                      <span className="text-violet-400 shrink-0">
                        <IconCheck />
                      </span>
                      {f}
                    </li>
                  ))}
                </ul>

                <a
                  href={PAYMENT}
                  target="_blank"
                  rel="noopener noreferrer"
                  className={`block w-full text-center py-3 rounded-xl font-semibold text-sm transition-all ${
                    plan.highlight ? "btn-primary text-white" : "btn-ghost text-slate-300"
                  }`}
                >
                  {plan.cta}
                </a>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── SOCIAL PROOF ───────────────────────────────────── */}
      <section className="py-32 bg-[#080810]">
        <div className="max-w-6xl mx-auto px-6">
          <div className="text-center mb-16 reveal">
            <div className="font-data text-[10px] text-slate-600 tracking-widest mb-4 uppercase">
              Social Proof
            </div>
            <h2 className="text-3xl sm:text-4xl font-bold">
              Trusted by data-driven teams
            </h2>
          </div>

          {/* logo strip */}
          <div className="flex flex-wrap justify-center gap-4 mb-20 reveal">
            {logos.map((name) => (
              <div
                key={name}
                className="px-7 py-3 rounded-xl text-slate-500 text-sm font-medium font-data tracking-wide"
                style={{
                  border: "1px solid rgba(255,255,255,.06)",
                  background: "rgba(255,255,255,.02)",
                }}
              >
                {name}
              </div>
            ))}
          </div>

          {/* testimonials */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
            {testimonials.map((t, i) => (
              <div
                key={t.name}
                className="card card-beam reveal p-7"
                style={{ transitionDelay: `${i * 0.12}s` }}
              >
                <div
                  className="text-4xl font-bold mb-4 leading-none"
                  style={{ color: "rgba(139,92,246,.55)" }}
                >
                  "
                </div>
                <p className="text-slate-300 text-sm leading-relaxed mb-6">{t.quote}</p>
                <div className="flex items-center gap-3">
                  <div
                    className="w-9 h-9 rounded-full flex items-center justify-center text-xs font-bold font-data shrink-0"
                    style={{
                      background:
                        "linear-gradient(135deg, rgba(124,58,237,.5), rgba(37,99,235,.4))",
                    }}
                  >
                    {t.avatar}
                  </div>
                  <div>
                    <div className="text-sm font-semibold text-white">{t.name}</div>
                    <div className="text-xs text-slate-500 mt-0.5">{t.title}</div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── CTA BANNER ─────────────────────────────────────── */}
      <section className="py-32 relative overflow-hidden">
        <div
          className="absolute inset-0"
          style={{
            background:
              "radial-gradient(ellipse 80% 100% at 50% 50%, rgba(109,40,217,.22) 0%, rgba(37,99,235,.1) 50%, transparent 80%), #080810",
          }}
        />
        <div className="line-grid absolute inset-0 opacity-40" />

        <div className="relative z-10 max-w-3xl mx-auto px-6 text-center reveal">
          <h2 className="text-4xl sm:text-5xl font-bold tracking-tight mb-5">
            Ready to bring your{" "}
            <span className="g-text">data to life?</span>
          </h2>
          <p className="text-slate-300 text-lg mb-10">
            Join 200+ data-driven teams using Rendara to communicate with impact.
          </p>
          <a
            href={PAYMENT}
            target="_blank"
            rel="noopener noreferrer"
            className="btn-primary inline-flex items-center gap-3 px-10 py-5 rounded-2xl font-bold text-lg text-white"
          >
            Get Your First Video →
          </a>
          <p className="text-slate-600 text-sm mt-6 font-data">
            Starting at $299 · 48h delivery · No commitment
          </p>
        </div>
      </section>

      {/* ── FOOTER ─────────────────────────────────────────── */}
      <footer
        className="py-10"
        style={{
          borderTop: "1px solid rgba(255,255,255,.05)",
          background: "#080810",
        }}
      >
        <div className="max-w-6xl mx-auto px-6 flex flex-col sm:flex-row items-center justify-between gap-4">
          <span className="font-data font-semibold text-lg g-text tracking-tight">Rendara</span>
          <span className="text-sm text-slate-600">© 2026 Rendara. All rights reserved.</span>
          <div className="flex gap-6 text-sm text-slate-500">
            <a href="#" className="hover:text-slate-300 transition-colors">Privacy</a>
            <a href="#" className="hover:text-slate-300 transition-colors">Terms</a>
          </div>
        </div>
      </footer>

    </div>
  );
}

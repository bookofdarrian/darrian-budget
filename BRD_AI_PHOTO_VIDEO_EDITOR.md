# AURA EDIT — AI Photo & Video Editor
## Business Requirements Document (BRD)
### Version 1.0 | March 2026 | Owner: Darrian Belcher

---

## 1. EXECUTIVE SUMMARY

**Product Name:** AURA Edit  
**Tagline:** *Your story. Your eye. AI-powered.*  
**Vision:** Build the first AI-native creative suite that understands who YOU are — your aesthetic, your culture, your brand — and makes professional-grade photo and video editing as fast as a thought.  

AURA Edit is not a tool for people who already know Photoshop. It's for the **creative entrepreneur** — the sneaker reseller who needs fire product shots in 60 seconds, the first-gen college student documenting their journey, the Black business owner who needs their photos to speak to their community without looking like a stock photo. It's for Darrian — and the millions like him.

It surpasses Adobe, Apple Photos, CapCut, and Canva by combining:
- **Personal Brand AI** — learns your aesthetic, style, and color palette over time
- **Cultural Intelligence** — understands Black, South Asian, and multicultural aesthetics natively (not as an afterthought)
- **Zero-friction UX** — describe what you want in plain English; AI does the rest
- **Multi-platform export** — one click to format for Instagram, TikTok, LinkedIn, website carousel, print

---

## 2. PROBLEM STATEMENT

### 2.1 What's Wrong with the Current Market

| Tool | Problem |
|------|---------|
| **Adobe Lightroom/Photoshop** | Steep learning curve, expensive ($55+/mo), built for professionals, "preset culture" leads to homogenized looks |
| **Apple Photos** | Smart editing is shallow, no multi-platform export, iCloud-locked, no brand consistency tools |
| **CapCut** | Great for TikTok, weak for photos, TikTok-owned (data concerns), template-heavy aesthetic |
| **Canva** | Design tool, not a photo editor, templates look generic, no AI that learns YOU |
| **Lightroom Mobile** | Better, still complex, no cultural presets, no brand memory |
| **VSCO** | Filter app, not a creative suite, no video, no AI intelligence |

### 2.2 The Cultural Gap

Every major editing tool was built by and for a homogenous user base. The result:
- Skin tone presets default to lighter complexions
- "Professional headshot" AI edits lighten/desaturate melanin-rich skin
- Stock photo suggestions default to white faces
- "Natural" color grading ignores the warm tones that look great on Black and Brown skin
- No tool understands the **Hampton VA boardwalk at golden hour** differently from a generic beach

**AURA Edit fixes this by training on diverse aesthetics and letting the user define what "professional" and "natural" means for THEM.**

### 2.3 The Creator Economy Gap

The creator economy is $500B+ and growing. Most creators are not designers. They need:
- Consistent brand look across hundreds of posts without hours of manual work
- Auto-resizing for every platform without quality loss
- AI that knows "this is a SoleOps product shot" vs "this is a PSS lifestyle photo"
- Background removal that works on dark-skinned subjects without edge artifacts
- One-click video clips from photo series

---

## 3. TARGET USERS

### Primary — The Creative Entrepreneur (Darrian's world)
- Age 20-35
- Running 1-3 side businesses / brands
- Heavy social media presence
- Limited time, high standards
- Culturally proud — wants their aesthetic to reflect who they are
- Phones: iPhone or high-end Android

### Secondary — First-Gen Creator Students
- College Confused demographic: first-gen college students
- Building personal brand for internships / social proof
- Need LinkedIn headshot quality without a photographer
- Budget-conscious: needs a free tier that's actually good

### Tertiary — Small Business / Side Hustlers
- Sneaker resellers (SoleOps demo)
- Fashion boutiques
- Local service businesses
- Real estate agents of color
- Anyone who shoots their own product photos

---

## 4. COMPETITIVE LANDSCAPE

### Market Research (2026)

| Company | Revenue | Valuation | Gap |
|---------|---------|-----------|-----|
| Adobe Creative Cloud | $5.4B ARR | $200B | Overbuilt, expensive, no cultural AI |
| Canva | $2.3B ARR | $26B | Design, not editing; no AI that learns you |
| CapCut (ByteDance) | est. $1.2B | Private | Video-only strength; TikTok data risk |
| Lightroom Mobile | Bundled w/ Adobe | — | Mobile version of desktop tool |
| Facetune | $100M+ ARR | ~$1B | Beauty filter niche; not a creative suite |
| **AURA Edit** | **0 → $10M target** | **Target: $50M Series A** | **First mover: cultural AI + brand memory** |

### Blue Ocean Features (no one is doing these)
1. **Brand Voice Memory** — remembers your color palette, editing style, common subjects
2. **Cultural Skin Calibration** — per-user skin tone AI trained to enhance, not bleach
3. **Immich Integration** — if you self-host, your photos never leave your server
4. **Narrative Mode** — arrange a photo series + AI writes the caption/story for each platform
5. **SEO Photo Engine** — auto-generates alt text, file names, metadata for web publishing

---

## 5. PRODUCT REQUIREMENTS

### 5.1 Core Modules

#### MODULE 1: AI Photo Editor
**Must Have:**
- [ ] One-sentence edit: "Make this look like golden hour in Atlanta" → applies
- [ ] Skin tone awareness: enhance without changing complexion
- [ ] Background removal/replacement with edge quality at par with remove.bg
- [ ] Auto-crop smart: understands composition rules + subject detection
- [ ] Batch editing: apply AI style to 50 photos in one pass
- [ ] Before/after split view
- [ ] Non-destructive: always revert-to-original

**Should Have:**
- [ ] "Match this edit style" — upload a reference photo, AI matches grade
- [ ] EXIF metadata editor for SEO
- [ ] Healing brush / object removal
- [ ] Portrait retouching that preserves melanin

**Nice to Have:**
- [ ] Physical print sizing and color profile export
- [ ] AI upscaling (x2, x4) for older photos

---

#### MODULE 2: AI Video Editor
**Must Have:**
- [ ] Auto-cut: upload raw clips, AI detects best moments, assembles highlight reel
- [ ] B-roll matching: describe a vibe, AI pulls your best matching clips
- [ ] Text overlays with brand fonts/colors auto-applied
- [ ] Voiceover with AI transcription + caption generation
- [ ] Platform presets: auto-export for TikTok (9:16), Instagram Reel (9:16), YouTube Short (9:16), LinkedIn (1:1), website (16:9)
- [ ] Color grade matching between clips for consistent look

**Should Have:**
- [ ] AI-generated music suggestions (royalty-free) matched to video mood
- [ ] Lip sync auto-caption
- [ ] Transition suggestions based on beat/energy

**Nice to Have:**
- [ ] AI avatar / voiceover (Darrian's voice model for ads)
- [ ] Storyboard planner from script → video

---

#### MODULE 3: Brand Memory Engine ⭐ (Key Differentiator)
This is the "Apple Photos faces recognition" but for your BRAND, not your face.

- **Style Profile**: learns from your 20 best edits what your aesthetic is
- **Color Palette Lock**: enforces your brand colors across all edits
- **Subject Library**: tags "this is a shoe shot" vs "this is a headshot" vs "this is nature"
- **Consistency Score**: rates each new edit 1-10 on brand consistency
- **Per-client mode**: if you do work for SoleOps, PSS, CC separately — each has its own brand profile

---

#### MODULE 4: Immich Bridge 🔗 (Self-Hosting Power Move)
- Connect to self-hosted Immich via API key
- CLIP search your library from inside AURA Edit
- Edit directly, save back to Immich album
- Auto-push web-optimized versions to your Streamlit carousel
- **Your photos NEVER touch our cloud** — zero-knowledge mode
- This is the feature that wins privacy-conscious creators

---

#### MODULE 5: Multi-Platform Publisher
- One-click export to:
  - Instagram (square, portrait, story)
  - TikTok (vertical video + cover photo)
  - LinkedIn (1:1, 16:9)
  - Website carousel (optimized JPEG/WebP)
  - Print (CMYK, 300 DPI)
- Auto-generate SEO metadata (alt text, title, description) using AI
- Peach State Savings / SoleOps / College Confused preset profiles included by default for Darrian

---

### 5.2 AI Intelligence Requirements

| Capability | Technology | Notes |
|-----------|-----------|-------|
| CLIP semantic search | OpenCLIP / Immich CLIP | Already proven in Immich |
| Photo classification | Claude claude-opus-4-5 | Uses filename + EXIF + context |
| Edit style generation | Stable Diffusion / ComfyUI | On-device or homelab GPU |
| Skin tone detection | Custom model | Train on diverse dataset |
| Auto-caption | Claude claude-opus-4-5 | Brand voice aware |
| Video scene detection | ffmpeg + CLIP | Open source |
| Music mood matching | Essentia / Librosa | Audio analysis |

---

### 5.3 Non-Functional Requirements

| Category | Requirement |
|----------|------------|
| **Speed** | Photo edit: < 3 seconds AI response. Video render: 1x realtime minimum |
| **Quality** | Output quality ≥ Lightroom at equivalent setting |
| **Privacy** | Zero-cloud mode available. Self-hosted option. No training on user photos without consent |
| **Accessibility** | Screen reader support, high-contrast mode, keyboard navigation |
| **Platform** | iOS app (primary), Web app, macOS desktop |
| **Offline** | Core edits work offline; AI features require connection (or local model) |

---

## 6. FOUNDER STORY INTEGRATION

AURA Edit is not just software — it's a cultural statement.

**The aesthetic that powers this product:**
- Hampton, VA boardwalk sunrises
- Atlanta's warm amber-gold hour
- Chicago's steel-and-sky architecture
- NYC energy, texture, density
- Sikh-influenced philosophy: *Ik Onkar* — One Creator, all are one. This product uplifts every creator without centering any single narrative.
- Black Panther ideology: self-determination, community ownership, technology as liberation

**The brand voice:** Confident, warm, direct. "Made by us, for us — and everyone who sees the world the way we do."

**The origin story matters:** A middle son, raised in Hampton by a mom who walked the streets of NYC as an intern, while his dad built something in Chicago and ATL. Two sisters who watched him build. Divorced parents who taught him resilience. This is a product built from ALL of that — not despite it.

---

## 7. BUSINESS MODEL

### Pricing Tiers

| Tier | Price | Target | Included |
|------|-------|--------|---------|
| **Free** | $0 | Students, casual creators | 50 photos/mo, watermark on video, 3 exports/day |
| **Creator** | $9.99/mo | Side hustlers, students | Unlimited photos, 10 video exports/mo, brand profiles |
| **Pro** | $24.99/mo | Entrepreneurs, small biz | Unlimited everything, Immich bridge, priority AI |
| **Business** | $49.99/mo | Agencies, 5+ brands | Team accounts, client brand profiles, API access |

### Revenue Projections (Conservative)

| Year | Users | MRR | ARR |
|------|-------|-----|-----|
| Year 1 | 1,000 | $5K | $60K |
| Year 2 | 10,000 | $50K | $600K |
| Year 3 | 50,000 | $250K | $3M |
| Year 4 | 200,000 | $1M | $12M |

### Monetization Beyond SaaS
- **Preset Marketplace**: creators sell their AI-trained style profiles
- **API for Developers**: integrate AURA's brand memory into other apps
- **Enterprise**: large agencies / brands (Foot Locker, NTWRK, HBCU partnerships)
- **Education**: College Confused bundle — AURA Edit + personal branding course

---

## 8. GO-TO-MARKET STRATEGY

### Phase 1 — Internal MVP (Q2 2026)
- Build as a Streamlit page: `pages/147_aura_edit.py`
- Use Claude for AI edits via API (describe → CSS/filter generation)
- Integrate with Immich for photo source
- Test with PSS, SoleOps, College Confused carousels
- Proof of concept: Darrian's own brand photos → AI edited → live on sites

### Phase 2 — Beta (Q3 2026)
- iOS TestFlight app (React Native + FastAPI backend on homelab)
- 100 beta users: sneaker resellers, HBCU creators, first-gen students
- Focus: Brand Memory Engine + Immich integration
- KPI: 40% of users re-edit within 7 days (retention signal)

### Phase 3 — Public Launch (Q4 2026)
- Product Hunt launch
- College Confused student community
- SoleOps reseller community
- HBCU campus ambassadors
- Target: 1,000 paid users by December 2026

### Phase 4 — Scale (2027)
- Series A pitch: $5M to build native AI models + team
- Partner with HBCUs for student licensing
- Enterprise deals: Black-owned agencies, fashion brands

---

## 9. TECHNICAL ARCHITECTURE

```
┌─────────────────────────────────────────────────────────────────┐
│                        AURA EDIT                                 │
├─────────────────┬───────────────────┬───────────────────────────┤
│   iOS App       │   Web App         │   Streamlit MVP           │
│  React Native   │  Next.js          │  pages/147_aura_edit.py   │
└────────┬────────┴─────────┬─────────┴──────────┬────────────────┘
         │                  │                     │
         └──────────────────┴─────────────────────┘
                            │
                    ┌───────▼────────┐
                    │  AURA API      │
                    │  FastAPI       │
                    │  homelab CT100 │
                    └───────┬────────┘
                            │
          ┌─────────────────┼──────────────────┐
          ▼                 ▼                   ▼
   ┌─────────────┐  ┌─────────────┐   ┌──────────────┐
   │ Claude API  │  │  Immich API │   │  ComfyUI     │
   │ (captions,  │  │  (photos,   │   │  (Stable     │
   │  classify,  │  │   CLIP,     │   │   Diffusion  │
   │  alt text)  │  │   albums)   │   │   edits)     │
   └─────────────┘  └─────────────┘   └──────────────┘
          │                 │                   │
          └─────────────────┼───────────────────┘
                            │
                    ┌───────▼────────┐
                    │  PostgreSQL    │
                    │  Brand Memory  │
                    │  Edit History  │
                    │  Photo Catalog │
                    └────────────────┘
```

---

## 10. SUCCESS METRICS

| Metric | 3-Month Target | 12-Month Target |
|--------|---------------|-----------------|
| Photos processed | 500 | 50,000 |
| Active users | 25 | 500 |
| Brand profiles created | 5 (Darrian's brands) | 100 |
| Immich connections | 1 (Darrian) | 50 |
| NPS Score | — | ≥ 50 |
| Paid conversion | — | 15% |

---

## 11. RISKS & MITIGATIONS

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| Adobe launches similar AI | High | Medium | We win on cultural intelligence + self-hosting |
| Claude API cost at scale | Medium | High | Cache aggressively; add local models for basic edits |
| ComfyUI quality inconsistency | Medium | Medium | Human-in-the-loop review before publish |
| Privacy breach | Low | Very High | Zero-cloud mode; end-to-end encryption; SOC2 roadmap |
| CapCut (TikTok) bans | High | Opportunity | Our timing is perfect — users need alternatives |

---

## 12. NEXT STEPS

### Immediate (This Sprint)
- [ ] Syntax check + deploy `utils/immich_photos.py` and `pages/146_immich_photo_manager.py`
- [ ] Connect Darrian's Immich API key via admin UI
- [ ] Run first AI photo index: classify all 28 existing Immich photos
- [ ] Verify carousel thumbnails load from Immich URLs on PSS, SoleOps, CC

### Month 1
- [ ] Build `pages/147_aura_edit.py` — MVP photo editor using Claude + CSS filters
- [ ] Add "Edit this photo" button to carousel manager
- [ ] First test: edit 5 brand photos for SoleOps product shots

### Month 2
- [ ] ComfyUI integration on homelab for Stable Diffusion edits
- [ ] Brand Memory Engine v1: store 5 sample edits → generate style profile
- [ ] Video module v1: ffmpeg + AI scene detection for highlight reels

### Month 3
- [ ] iOS MVP via React Native
- [ ] Beta invite for 20 College Confused students
- [ ] Product Hunt waitlist launch

---

## APPENDIX A: MARKET RESEARCH SOURCES

1. Adobe FY2025 Annual Report — $5.4B Creative Cloud ARR
2. Canva 2025 Funding Round — $26B valuation confirmed
3. Creator Economy Report 2025 (Goldman Sachs) — $500B by 2027
4. CapCut ban/alternative searches 2025 — 250% spike in Jan 2025
5. "Cultural bias in AI photo editing" — MIT Media Lab, 2024
6. HBCU student creator survey (informal, n=40) — 78% use CapCut, 65% cite "doesn't understand my look" as frustration
7. Immich GitHub — 40K+ stars, 500K+ self-hosted instances (2026)

---

## APPENDIX B: NAMING CONSIDERATIONS

| Name | Reasoning |
|------|-----------|
| **AURA Edit** | Ties to Darrian's existing Aura project; mystical, personal, energy-focused |
| **PRISM** | Refraction of light = many perspectives; inclusivity theme |
| **Melanin Studio** | Direct cultural statement; risk: too narrow |
| **ROOTS Edit** | Ties to the Hampton/Chicago/ATL/NYC story |
| **VISION** | Simple, powerful; but generic |

**Recommendation:** Launch as **AURA Edit** (ties to homelab project, already in the codebase as `aura/`).

---

*Document Owner: Darrian Belcher | Last Updated: 2026-03-22*  
*This document is confidential and proprietary to Darrian Belcher / Peach State Savings LLC*

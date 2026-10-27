# Theme synthesis

Model: `anthropic:claude-sonnet-5-5`. For each theme, the model read the sampled reviews tagged with it (complaint themes: negative and mixed sentiment only; education: all sentiments) and wrote a summary, sub-issues, quotes, likely causes and an opportunity. Weighted shares and intervals come from `insights/metrics.json`.

Reviews date from July 2023 to August 2024; some issues may have been fixed since.

How to read this:

- **Review ids and quotes are checked in code.** Every id belongs to the theme's input, and every quote appears word for word in its review.
- **Sub-issue counts are computed in code** from the ids the model listed. They are a lower bound: the model may not list every review that mentions a sub-issue. Each theme shows how many of its reviews the sub-issues cover.
- **Weighted share of theme** re-weights each sub-issue's reviews by band × quarter (the same weights as `insights.py`), so it estimates the share across all cleaned reviews in the theme. The sample column over-represents 1–3 star reviews.
- **Likely causes are hypotheses** drawn from review text, not verified against product data.
- Theme labels come from the classifier; intervals cover sampling error only.

## Wrong, unreliable or outdated answers (`answer_quality`)

*Complaints that responses are factually wrong, hallucinated, inconsistent, poor at following instructions, or based on outdated training data (e.g. a 2021 or 2022 cutoff).*

| Weighted share of… | Estimate (95% CI) |
|---|---|
| All reviews | 15.8% (13.5%–18.3%) |
| Complaint reviews | 30.8% (26.8%–35.2%) — rank 1 of 10 |
| 1–2 star reviews | 29.0% (24.8%–33.0%) |

Complaint-share trend: no clear change: 36.1% in 2023Q4 → 31.5% in 2024Q2.

Synthesised from 343 sampled reviews (negative and mixed reviews only).

**Summary.** Users repeatedly report that the app gives wrong or inconsistent answers (math, science, grammar, local facts, code, translation) and keeps stubbornly repeating errors even after correction. A second large cluster complains about the stale knowledge cutoff (Sept 2021 / Jan 2022) and lack of live web data, which leaves answers outdated or wrongly framed. Many also say it ignores instructions, forgets earlier context, switches language or model unexpectedly, and that quality seems to have declined over time, so they feel they must double-check everything.

| Sub-issue | Reviews in sample | Weighted share of theme (at least) |
|---|---:|---:|
| Outdated knowledge cutoff / no live data | 68 (20%) | 21% |
| Factual, math and domain errors / hallucinations | 74 (22%) | 23% |
| Ignores instructions / repeats mistakes after correction | 25 (7%) | 6% |
| Forgets context / inconsistent across chats and sessions | 18 (5%) | 3% |
| Quality decline, 'dumber' model, wrong language or model switching | 28 (8%) | 5% |

Sub-issues cover 60% of this theme's sampled reviews (57% weighted).

**Quotes**

> "I just ask chatgpt a addition question 15947+62851 is then answer me that 78898 please correct this fault" — 1 star, `fafed023-c54c-44c4-b445-bf88589cbb07`

> "I can ask a question tell it no that's not what I'm asking or no that's incorrect and it will double, triple quadruple, etc. down." — 1 star, `ff62e102-69a5-4da0-9118-915a131af8fc`

> "Still sayings that the president of India Ram Nath" — 4 star, `4e506508-47e6-49c5-9d17-a29a3e9ff1d0`

**Likely causes (hypotheses, not verified)**

- Hypothesis: the model's training-data cutoff and lack of default web browsing cause stale answers, and the model's disclaimers about its cutoff are applied even to questions that predate it.
- Hypothesis: LLMs generating text probabilistically (not computing) lead to arithmetic, logic and niche local-fact errors, with weaker performance on low-resource languages and regional topics.
- Hypothesis: sycophantic or over-apologetic behavior (agreeing then repeating the same answer) makes corrections feel ineffective and fosters an impression of lying.
- Hypothesis: free-tier use of a smaller model (GPT-3.5), silent fallback from GPT-4 to 3.5, and model updates or safety tuning make quality feel inconsistent or worse over time.
- Hypothesis: limited context window and weak or inconsistent memory features cause forgotten instructions and details mid-chat or across sessions.
- Hypothesis: the mobile app may differ from the web version (different model, system prompt, or language auto-detection), explaining wrong-language replies and answer discrepancies.

**Opportunity.** Make freshness and reliability visible and fixable by enabling web search by default with source citations, showing the active model and cutoff clearly, preventing silent downgrades, and adding stronger tool use (calculator, verification) and better memory for instruction-following.

## Crashes, errors and connectivity (`crashes_errors`)

*The app not working reliably: crashing, freezing, not opening, showing error messages, losing connection, stopping mid-response, or being slow and laggy.*

| Weighted share of… | Estimate (95% CI) |
|---|---|
| All reviews | 10.0% (8.5%–11.8%) |
| Complaint reviews | 20.4% (17.4%–23.7%) — rank 2 of 10 |
| 1–2 star reviews | 27.3% (23.1%–31.1%) |

Complaint-share trend: no clear change: 19.0% in 2023Q4 → 23.9% in 2024Q2.

Synthesised from 243 sampled reviews (negative and mixed reviews only).

**Summary.** Users report the app failing to work reliably: crashing or closing on launch, hanging on infinite loading or blank screens, and showing generic errors ('An error has occurred', 'request is not allowed', 'request is invalid') that often persist for days despite reinstalls. A very common complaint is false 'network error' or 'no connection' messages when the internet is fine and the web version works on the same network. Slowness is also widespread, including slow replies, lag, keyboard lag, long auto-scroll when opening chats, and responses that stop mid-answer, and many paying subscribers say the app is unusable for them.

| Sub-issue | Reviews in sample | Weighted share of theme (at least) |
|---|---:|---:|
| Crashes, force-closes and app not opening | 31 (13%) | 14% |
| Infinite loading, blank screens and freezes | 21 (9%) | 6% |
| Generic error messages blocking use (try again later / request not allowed / invalid) | 55 (23%) | 21% |
| False network or connection errors despite good internet | 29 (12%) | 11% |
| Slow responses, lag and stalled replies | 45 (19%) | 22% |

Sub-issues cover 72% of this theme's sampled reviews (72% weighted).

**Quotes**

> "Crashes... So you clear the storage, it crashes. As in it opens for just a millisecond and goes back to the home screen." — 2 star, `855d06da-50ac-4e4f-887b-9ef5c5cc6eda`

> "Does not work due to "network errors", no network is all good according to hmm let me think, everything else lol, it is the app. Same paid account works via web." — 1 star, `29fe8aa1-f292-42cc-ac47-d8ba0d410816`

> ""An error has occurred. Please try again later.", with a big exclamation symbol in the middle. No reboots helped. Nor cache wiping." — 1 star, `96985ce8-c6c0-429e-8f1b-51ec1688c3ad`

**Likely causes (hypotheses, not verified)**

- Hypothesis: server-side overload, rate limiting or outages surface as generic client errors ('try again later', 'request is not allowed'), which would explain why they appear suddenly, persist for days and hit paying users too.
- Hypothesis: the app's connectivity check or error handling misclassifies backend or timeout failures as 'network error', producing false offline messages when the web version works on the same network.
- Hypothesis: certain device, OS or ROM combinations (Pixel 7/8, Galaxy S23, Samsung foldables, low-end phones, LineageOS or no Play Services) hit compatibility bugs that cause launch crashes or endless loading.
- Hypothesis: corrupted local state, cached chat history or account data persists across cache clears and reinstalls, causing crashes on open and failures when loading old conversations.
- Hypothesis: long conversations are rendered inefficiently (full load then auto-scroll, no chunking) and the main thread is overloaded, causing slow scrolling, keyboard lag, battery drain and freezes.
- Hypothesis: recent app updates introduced regressions, since many reviews say the problem began right after an update.

**Opportunity.** A PM could prioritise a reliability push that fixes false network-error detection, replaces generic error messages with specific actionable ones, investigates launch crashes by device and OS, and optimises long-chat loading and scrolling.

## Pricing, subscription and usage limits (`pricing_limits`)

*Feedback about subscription cost and value, billing problems, regional affordability, paywalled features, message caps and model switching on paid or free plans.*

| Weighted share of… | Estimate (95% CI) |
|---|---|
| All reviews | 9.1% (7.2%–11.2%) |
| Complaint reviews | 15.3% (12.3%–18.8%) — rank 4 of 10 |
| 1–2 star reviews | 17.6% (14.3%–21.2%) |

Complaint-share trend: no clear change: 12.5% in 2023Q4 → 21.1% in 2024Q2.

Synthesised from 155 sampled reviews (negative and mixed reviews only).

**Summary.** Users repeatedly say the subscription is too expensive for the value, especially outside the US (India, Egypt, Pakistan, Philippines, Indonesia), and that paying does not remove message caps or guarantee reliable access to GPT-4. Many Plus subscribers report purchases not being recognised, being silently downgraded to 3.5 or defaulted to 4o, and promised features such as voice, images and DALL-E not appearing. Free-plan users are frustrated by tightening limits and paywalled features like image generation, photo input and voice, while billing, cancellation and refund problems add to the distrust.

| Sub-issue | Reviews in sample | Weighted share of theme (at least) |
|---|---:|---:|
| Price too high / regional affordability and lack of cheaper tiers | 27 (17%) | 20% |
| Message caps and rate limits, including on paid plans | 29 (19%) | 15% |
| Model downgrade or defaulting (GPT-4 to 3.5 or 4o, outdated cutoff) | 19 (12%) | 9% |
| Features paywalled or promised but missing after paying (image, photo, voice) | 21 (14%) | 19% |
| Billing, purchase recognition, cancellation and refunds | 19 (12%) | 12% |

Sub-issues cover 68% of this theme's sampled reviews (71% weighted).

**Quotes**

> "So you are telling me I'm paying $20 a month for 40 messages every 3 hours? Really? What a scam" — 1 star, `e9aaa098-08d3-4924-b219-c2e0606fd62c`

> "chatGPT plus is about a quarter of the salary in Egypt" — 5 star, `72dca83c-c019-4a3a-94d9-61d06ba223fc`

> "I *pay* for GPT4 and I should be able to have it as the default." — 1 star, `3b40ca44-78b3-473f-9499-8c2ad45e3fde`

**Likely causes (hypotheses, not verified)**

- Hypothesis: a single USD-anchored price with little regional adjustment makes Plus feel unaffordable in lower-income markets, and local payment methods are missing or limited in some countries.
- Hypothesis: capacity constraints on GPT-4 and GPT-4o lead to hard caps and fallbacks to 3.5 that are not clearly communicated, so paying users feel the premium promise is not delivered.
- Hypothesis: entitlement sync between Google Play purchases, OpenAI accounts and the Android app is fragile (wrong Play account, login limitations, delayed upgrade), so Plus does not show after purchase.
- Hypothesis: staged feature rollouts (voice, DALL-E, image input) and marketing demos create expectation gaps when paying users do not yet have the features.
- Hypothesis: frequent changes to free-tier limits and features, with little in-app messaging about what each plan includes, make users suspect deliberate degradation to push upgrades.

**Opportunity.** Introduce regionally priced or lighter, cheaper tiers, make caps, active model and plan entitlements transparent in the app, and fix Android purchase-sync, default-model and cancellation flows so paying users reliably get what they bought.

## Login, sign-up and account problems (`login_account`)

*Difficulty signing in, signing up, staying logged in, verifying identity, or recovering or deleting accounts.*

| Weighted share of… | Estimate (95% CI) |
|---|---|
| All reviews | 5.4% (4.4%–6.5%) |
| Complaint reviews | 11.4% (9.4%–13.8%) — rank 6 of 10 |
| 1–2 star reviews | 22.5% (19.0%–26.1%) |

Complaint-share trend: no clear change: 11.8% in 2023Q4 → 9.1% in 2024Q2.

Synthesised from 143 sampled reviews (negative and mixed reviews only).

**Summary.** Users are blocked at the front door of the Android app: they cannot sign in or sign up because of 'install Chrome' browser errors, login loops that return to the sign-in screen, and misleading date/time or Play Store errors. Phone verification (rejected numbers, 'landline' or 'too many accounts' messages, unsupported countries or carriers), birth-date entry failures, and unexplained logouts add to the friction. Account recovery, deletion and support are also seen as dead ends, and many reviewers say the web version works fine while the app does not.

| Sub-issue | Reviews in sample | Weighted share of theme (at least) |
|---|---:|---:|
| 'Install Chrome' / compatible browser error and Firefox redirect failures | 16 (11%) | 12% |
| Login loops, stuck/blank screens and non-responsive sign-in | 25 (17%) | 15% |
| Misleading errors: date/time, Play Store update, generic 'something went wrong', VPN | 16 (11%) | 10% |
| Phone number and birth date verification rejected or unwanted | 27 (19%) | 15% |
| Unexpected logouts, lost accounts, deletion/recovery and support dead ends | 16 (11%) | 14% |

Sub-issues cover 69% of this theme's sampled reviews (66% weighted).

**Quotes**

> "It seems the app checks for the presence of chrome but uses the default browser, Firefox, you need to remove this check, it's daft" — 3 star, `b56e5d22-68f3-4395-98e0-25158d421329`

> "After multiple try it say your number is linked to maximum account but the fact is I was not able to link it with my any account successfully at first place." — 1 star, `1aa445aa-6113-4255-a2b9-d0515aa2008e`

> "Every time when successfully logging in, it just brings me back to the sign-in-menu." — 1 star, `85df9517-1079-4a6d-bb2d-35f687716585`

**Likely causes (hypotheses, not verified)**

- The app's login flow may check for Chrome Custom Tabs/a specific browser package and fail on Chromebooks, Firefox/Fennec/Kiwi defaults, or devices where Chrome is disabled, even when a compatible browser is present.
- The OAuth redirect back from the browser to the app may fail on non-Chrome default browsers or on certain devices/ROMs, leaving users on the sign-in screen after authenticating.
- A generic catch-all error ('date and time', 'something went wrong', 'update Play Store') may be shown for unrelated failures such as Play Services/Integrity checks, network issues, or VPN/IP blocks, so users cannot self-diagnose.
- Anti-abuse and phone verification rules (VOIP/landline detection, per-number account caps, regional SMS delivery gaps, VPN blocking) may produce false positives and unsupported-country dead ends.
- Early app versions may have lacked Microsoft/email-password sign-in parity with the web, and age/birth-date form bugs may block onboarding on some devices.
- Session token expiry or account-state handling may log users out unexpectedly and give no clear recovery or support path for deleted or deactivated accounts.

**Opportunity.** A PM could prioritise a robust, browser-agnostic sign-in flow with specific, actionable error messages, working fallbacks for phone verification and birth-date entry, and a clear self-serve path for account recovery, deletion and support.

## Bias, censorship and privacy concerns (`bias_censorship_privacy`)

*Objections to perceived political, religious or ideological bias, over-restrictive or preachy content policies, offensive content about groups, and data collection or privacy practices.*

| Weighted share of… | Estimate (95% CI) |
|---|---|
| All reviews | 3.3% (2.5%–4.3%) |
| Complaint reviews | 7.1% (5.3%–9.1%) — rank 10 of 10 |
| 1–2 star reviews | 11.8% (9.0%–14.8%) |

Complaint-share trend: no clear change: 9.7% in 2023Q4 → 5.4% in 2024Q2.

Synthesised from 90 sampled reviews (negative and mixed reviews only).

**Summary.** Users object most to over-restrictive content filtering that blocks harmless requests (creative writing, images, roleplay, medical or controversial topics) and adds preachy caveats and moralising. A second large group perceives political, religious or ideological bias, from both left and right and in both directions on religion and geopolitics. A third group distrusts data practices, especially phone-number and personal-info demands at signup, with some reporting spam or tracking, and many uninstall before using the app.

| Sub-issue | Reviews in sample | Weighted share of theme (at least) |
|---|---:|---:|
| Over-censorship and refusals on harmless or adult requests | 26 (29%) | 26% |
| Lecturing, moralising and paternalistic tone | 10 (11%) | 7% |
| Perceived political or ideological bias (left, right, 'woke') | 21 (23%) | 24% |
| Religious, ethnic and geopolitical bias or offensive content | 7 (8%) | 5% |
| Phone number, personal data and privacy distrust | 22 (24%) | 28% |

Sub-issues cover 84% of this theme's sampled reviews (83% weighted).

**Quotes**

> "Why do you need my phone number?? 😡 Explain, I'm very curious as to why you have to invade my personal details." — 1 star, `d6ae0c13-f12f-47f9-ad61-f4f4cd605490`

> "I am an adult not a child so theres no need for an A.I. assistant to sensor me" — 3 star, `71aa88dc-cdea-48b1-a5ef-6b51b21fadf9`

> "Ask it about Trump and it won't tell you anything. Ask about Kamala and suddenly it knows all of it." — 1 star, `739b4cb1-908f-492d-9dec-f56d55a6aa5b`

**Likely causes (hypotheses, not verified)**

- Hypothesis: safety filters are tuned conservatively and applied uniformly, so fiction, art, medical and historical requests trigger refusals meant for genuinely harmful content.
- Hypothesis: users cannot see why a request was refused or adjust strictness (no adult mode or per-user settings), so refusals feel arbitrary and paternalistic.
- Hypothesis: training data, RLHF and neutrality guardrails produce answers that different political, religious and cultural groups each read as slanted against them, and inconsistent handling across topics reinforces the perception.
- Hypothesis: mandatory phone verification and account creation before any value is shown is read as data harvesting, and an anti-abuse measure is not explained to users.
- Hypothesis: reports of spam texts, memory features and unclear data-use messaging fuel the belief that personal data is collected, profiled or sold.

**Opportunity.** A PM could reduce churn by making refusals transparent and configurable (clear reasons, an adult or creative mode, less boilerplate moralising) while explaining the purpose of phone verification and offering a lighter-friction, privacy-forward signup path.

## Image generation and multimodal requests (`image_multimodal`)

*Requests or complaints about creating, showing or understanding images, documents and other media.*

| Weighted share of… | Estimate (95% CI) |
|---|---|
| All reviews | 7.8% (6.0%–9.8%) |
| Complaint reviews | 13.4% (10.0%–16.9%) — rank 5 of 10 |
| 1–2 star reviews | 5.6% (3.6%–7.7%) |

Complaint-share trend: no clear change: 11.3% in 2023Q4 → 17.4% in 2024Q2.

Synthesised from 94 sampled reviews (negative and mixed reviews only).

**Summary.** Users overwhelmingly want ChatGPT on Android to do more with images and other media: generate pictures, show images or diagrams in answers, and accept photos or documents as input. Many reviewers who are otherwise positive cap their rating at 3-4 stars because of the missing capability. Paying and free users alike are frustrated by paywalls, upload caps, restrictive content filters and poor image output quality.

| Sub-issue | Reviews in sample | Weighted share of theme (at least) |
|---|---:|---:|
| No image generation / wants image creation | 19 (20%) | 28% |
| Image generation paywalled or access-limited | 11 (12%) | 13% |
| Poor, buggy or over-restricted image results | 16 (17%) | 12% |
| Cannot show images, diagrams or other media in answers | 27 (29%) | 19% |
| Photo/document upload missing or capped | 27 (29%) | 30% |

Sub-issues cover 99% of this theme's sampled reviews (96% weighted).

**Quotes**

> "all fine and well until image generation is locked behind paid version" — 2 star, `a13b860c-30d7-4d2b-b079-64a7565ef27b`

> "I can only put in 3 images every 22 hours" — 2 star, `d7f872d5-432f-4b63-b3b3-e550518f0a38`

> "the stupid image generator arguing with itself and then saying it can't tell you why it can't generate an image" — 1 star, `bf39be83-c9d7-4621-b598-911db894ac21`

**Likely causes (hypotheses, not verified)**

- Reviews may reflect an older app version where image generation and photo upload were not yet available on Android or were limited to paid tiers, creating a gap between what users saw online and what they could do.
- Users may see social-media demos of image generation and expect it in the free app, leading to disappointment when the feature is unavailable or gated.
- Strict content-policy filters and opaque refusal messages may cause harmless prompts (e.g. art styles) to be rejected without explanation.
- Rate limits on image uploads and generation (per-hour or per-day caps) may be hitting students and other heavy photo users who rely on the feature for homework.
- Image generation quality and prompt adherence may be inconsistent, with models misinterpreting prompts or ignoring corrections.

**Opportunity.** Make photo input and a basic level of image generation or inline visuals available to free users with clear, generous limits and transparent explanations when requests are refused or capped.

## Education and homework help (`education`) — positive theme

*Reviews about using ChatGPT for studying, homework, research, exam prep, learning new skills or languages, or as a personal tutor.*

| Weighted share of… | Estimate (95% CI) |
|---|---|
| All reviews | 19.3% (16.5%–22.5%) |
| Complaint reviews | 7.5% (4.9%–10.5%) — rank 9 of 10 |
| 1–2 star reviews | 3.0% (1.6%–4.5%) |

Complaint-share trend: no clear change: 10.1% in 2023Q4 → 5.7% in 2024Q2.

Synthesised from 178 sampled reviews (all sentiments).

**Summary.** Students and self-learners use ChatGPT as an always-available tutor for homework, assignments, exam prep (SAT, IIT JEE, board exams, GCSEs), research, language learning and coding. They value the plain-language, step-by-step explanations, the speed compared with searching Google, and the fact that it is free and ad-free. Voice conversation and the ability to re-ask until a concept clicks make it feel like a personal teacher.

| Sub-topic | Reviews in sample | Weighted share of theme (at least) |
|---|---:|---:|
| Homework, assignments and projects | 19 (11%) | 13% |
| Exam prep and test performance | 9 (5%) | 6% |
| Simple explanations and doubt-clearing (personal tutor) | 16 (9%) | 13% |
| Language learning and voice practice | 10 (6%) | 7% |
| Research, study planning and coding help | 11 (6%) | 7% |

Sub-topics cover 35% of this theme's sampled reviews (44% weighted).

**Quotes**

> "since I started using this application, I am able to get my own teacher anytime, anywhere." — 5 star, `c1da59d6-96c4-4090-988e-3334bbb77fdc`

> "it is helpful to learn on how did chatGPT solved it ..to do it next time by your self" — 5 star, `f968aac7-d195-4d08-bc5c-987ebd9a7211`

> "The voice chat integration is very useful to understand concepts while studying" — 5 star, `574739da-cbeb-451a-a441-15351a2f2bea`

**Likely causes (hypotheses, not verified)**

- Hypothesis: the conversational format lets learners ask follow-up questions in their own words and get simplified explanations, which feels more like tutoring than searching.
- Hypothesis: being free, ad-free and fast on mobile removes friction for students who need quick help at any hour.
- Hypothesis: voice mode and multilingual support make the app useful for language practice and for learners who struggle with written English.
- Hypothesis: summarising content, building timetables and generating key points saves students hours compared with skimming web results.
- Hypothesis: early-stage enthusiasm from first-time users, many of them school-age, inflates praise for general usefulness.

**Opportunity.** Build a dedicated study mode on mobile with step-by-step explanations, photo-based question input, proper maths and science notation rendering, saved study sessions and voice-based language practice to deepen the tutor experience students already value.

# See your site live for FREE on Render 🚀 (test drive)

This guide puts your Nail Art Studio site **online in about 15 minutes**, at a
free web address like `https://miss-universe-nail-studio.onrender.com`, so you
can open it on your phone, click around, and share it with people.

No coding needed — it's all clicking buttons on a website.

---

## ⚠️ Read this first — what "free" means here

Render's free plan is **perfect for testing**, but it has two quirks you should
know about up front so nothing surprises you:

1. **Anything you add disappears.** If you log into the admin panel and add your
   own designs or upload photos, they'll **vanish** the next time the site
   restarts or goes to sleep. The site always resets back to the **16 demo
   designs** (which reappear automatically, so it never looks empty).
2. **It "sleeps" when nobody's looking.** After ~15 minutes with no visitors,
   Render puts the site to sleep to save resources. The **next** visit then
   takes **30–60 seconds** to wake up (you'll see a loading spinner), after
   which it's fast again.

**In short:** this is a live *preview* to see how everything looks and works —
not the permanent home for your real designs.

> 💎 **When you're ready for the real thing** (your own designs that stay
> forever, your own domain, no sleeping), use the
> [Oracle Cloud guide](DEPLOY_ORACLE.md) — it's also free but keeps your data
> permanently. Or upgrade this same Render site to a paid plan (~$7/month) later.

---

## The one thing you need first: your code on GitHub

Render builds your site straight from **GitHub** (a free website that stores
code), so the project needs to live there first. This is the only slightly
fiddly part, and **I can do almost all of it with you** —

> 👉 **Just tell me "set up GitHub" and I'll walk you through it step by step.**
> It's a free account, a new empty repository, and uploading this folder — about
> 5 minutes together. Your secret `.env` file is deliberately left out, so
> nothing private ever goes online.

Once your code is on GitHub, come back and continue below. ⬇️

---

## Part 1 — Create a Render account

1. Go to **<https://render.com>** and click **Get Started**.
2. Choose **Sign up with GitHub** (easiest — it connects the two for you).
3. Approve the permission screen so Render can see your repositories.

Free — no card required.

---

## Part 2 — Deploy with one click (the Blueprint)

Your project already contains a file called **`render.yaml`** that tells Render
exactly how to build everything. Render calls this a **Blueprint**.

1. In the Render dashboard, click **New +** (top-right) → **Blueprint**.
2. Find and select your Nail Studio repository, then click **Connect**.
3. Render reads `render.yaml` and shows a short form. It will ask you to fill in
   **two** boxes (these become your admin login):

   | Box              | What to type                                      |
   |------------------|---------------------------------------------------|
   | `ADMIN_EMAIL`    | the email you want to log in with                 |
   | `ADMIN_PASSWORD` | a strong password you'll remember                 |

   Everything else (your WhatsApp number, contact details, a secure random
   signing key, etc.) is filled in **automatically**.
4. Click **Apply** (or **Create**).

> Important: use **Blueprint**, not the ordinary **Web Service** form. The
> Blueprint already marks this as a Python website. Choosing the ordinary form
> can make Render guess Node.js and look for a `package.json` file that this
> project does not have.

Render now builds your site. The first build takes about **2–5 minutes** — you
can watch the progress log scroll by. When it finishes you'll see **"Live"** with
a green dot. ✅

---

## Part 3 — You're live! 🎉

1. At the top of your service page, Render shows your web address — something
   like **`https://miss-universe-nail-studio.onrender.com`**. Click it.
2. Your site opens, complete with the demo catalogue. 🎊
3. Add **`/admin`** to the end of the address to reach the admin panel, and log
   in with the **email and password** you entered in Part 2.

> ⏳ **First load feels slow?** If the site has been asleep, the very first click
> takes 30–60 seconds to wake it. Totally normal on the free plan — it's quick
> after that.

> 🧪 **Remember the reset:** feel free to add designs and play around, but don't
> put in your real catalogue yet — it won't stick on the free plan (see the note
> at the top).

---

## Part 4 *(optional)* — Use your own domain

Want it at **`missuniverse.dpdns.org`** instead of the long `.onrender.com`
address? You can, even on the free plan:

1. In Render, open your service → **Settings** → **Custom Domains** → **Add
   Custom Domain**.
2. Type `missuniverse.dpdns.org` and confirm. Render shows you a **target**
   value to point at (usually something like `your-app.onrender.com`).
3. In your **DigitalPlat dashboard**, open DNS for `missuniverse.dpdns.org` and
   add a **CNAME** record:

   | Type    | Name / Host   | Value / Points to            |
   |---------|---------------|------------------------------|
   | `CNAME` | `missuniverse`| *(the target Render gave you)* |

   - ⚠️ Just like before: if there's a **cloud/"Proxy" toggle** (Cloudflare), set
     it to **"DNS only" (grey cloud)**, not "Proxied".
4. Back in Render, click **Verify**. Within a few minutes Render gives your
   domain a free HTTPS padlock 🔒 automatically.

*(The free-plan sleeping and data-reset still apply on your custom domain — it's
still the same free site, just with a nicer address.)*

---

## Everyday use

- **Log in:** your address + `/admin`.
- **See build logs / restart:** your service page in the Render dashboard has
  **Logs** and a **Manual Deploy** button.
- **Update the site after a change:** if you (or I) update the code on GitHub,
  Render notices and **redeploys automatically**. Nothing for you to do.

---

## Troubleshooting

**The build failed.**
- Open the **Logs** tab on your Render service and read the last few red lines.
  Copy them to me and I'll tell you exactly what to fix.
- If it mentions a **Python version**, add an environment variable in Render:
  **Settings → Environment → Add** → key `PYTHON_VERSION`, value `3.13.4` →
  save (it redeploys).

**The site takes ages to open.**
- It was asleep and is waking up (free-plan behaviour). Give it up to a minute.
  It stays fast while people are using it.

**The designs I added are gone.**
- Expected on the free plan — the site reset and restored the demo designs. This
  is the main reason it's for testing only. For designs that stay forever, use
  the [Oracle Cloud guide](DEPLOY_ORACLE.md) or upgrade to a Render paid plan
  with a disk.

**I can't log into `/admin`.**
- Use the exact `ADMIN_EMAIL` and `ADMIN_PASSWORD` you typed in Part 2. To
  change them: Render → your service → **Environment**, edit the values, and
  save (it redeploys with the new login).

**"Blueprint" option / `render.yaml` not detected.**
- Make sure `render.yaml` is in the **top level** of your GitHub repository (it
  is, in this project). Then use **New + → Blueprint** (not "Web Service").

---

## Safety notes (already handled for you)

- Your **admin password** and the site's **signing key** are stored only inside
  Render's private settings — never in your code or on GitHub.
- The site runs in **production mode** with a secure HTTPS padlock and secure
  login cookies, exactly like a real deployment.
- Your private `.env` file is never uploaded to GitHub (it's ignored on
  purpose), so no secrets ever leak.

---

*That's it! Click around, show it off, and when you're ready to make it
permanent just say the word and we'll move it to a plan that keeps your real
designs forever.*

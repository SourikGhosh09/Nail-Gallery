# Putting your site online — free, on Oracle Cloud ☁️

This guide takes your Nail Art Studio website **live on the internet**, at your
free domain **`https://missuniverse.dpdns.org`**, with a proper HTTPS padlock 🔒.

- **Hosting cost:** ₹0 / $0 — Oracle Cloud's *Always Free* tier never expires
  and is never charged.
- **Domain cost:** ₹0 too — you're using the free **`missuniverse.dpdns.org`**
  from DigitalPlat. So this whole setup is genuinely free. 🎉
- **Time:** about 60–90 minutes the first time. You do it once.

You do **not** need to know how to code. Every command below is copy‑paste.

### How it fits together

```
  Your customer's phone
          │  types https://missuniverse.dpdns.org
          ▼
  Your domain name  ──DNS──►  Your free Oracle server
                                      │
                                 [ Caddy ]  ← gets the free HTTPS padlock 🔒
                                      │
                                 [ your app ]  ← the website + admin panel
```

You'll set up the four boxes from top to bottom.

---

## Before you start — a checklist

- [x] A **domain name** — you've got **`missuniverse.dpdns.org`** free from DigitalPlat ✅
- [ ] A **credit or debit card**. Oracle asks for it *only to verify you're a
      real person*. The Always Free resources you'll use are **not charged**.
- [ ] Your project code (this folder). We'll get it onto the server in Part 5.

> 💡 **Tip:** Do the steps in order. If you get stuck, the
> [Troubleshooting](#troubleshooting) section at the end covers the common snags.

---

## Part 1 — Create your free Oracle server

1. Go to **<https://www.oracle.com/cloud/free/>** and click **Start for free**.
2. Sign up. When asked, pick a **Home Region** that's close to your customers
   (e.g. *India West (Mumbai)* or *India South (Hyderabad)*). You can't change
   this later, so choose well.
3. Complete the card verification. (Again: Always Free is not charged.)
4. Once you're in the **Oracle Cloud Console**, click the ☰ menu (top-left) →
   **Compute** → **Instances** → **Create instance**.
5. Fill in the instance form:
   - **Name:** `nailstudio`
   - **Image and shape** → click **Edit**:
     - **Image:** *Canonical Ubuntu* (22.04 or 24.04).
     - **Shape:** click **Change shape** → **Ampere** → **VM.Standard.A1.Flex**.
       Set it to **1 OCPU** and **6 GB** memory. *(This is the free ARM
       machine — more than enough.)*
       - If you see **“Out of host capacity”**, either try again later, or pick
         **Ampere** ▸ can't be found → switch the shape series to **Specialty
         and previous generation** → **VM.Standard.E2.1.Micro** (the free x86
         option). Both work fine for this app.
   - **Add SSH keys:** choose **Generate a key pair for me**, then click
     **Save private key** and **Save public key**. **Keep the private key file
     safe** — it's the "password" to your server. Put it somewhere you won't
     lose it, e.g. `C:\Users\YOU\nailstudio-key.key`.
6. Click **Create**. After a minute the instance turns **green (Running)**.
7. On the instance page, copy the **Public IP address** (looks like
   `140.238.x.x`). **Write it down** — you'll use it several times. We'll call it
   **YOUR_SERVER_IP**.

---

## Part 2 — Open the network (ports 80 & 443)

Two "doors" must be opened so the internet can reach your site: one in Oracle's
web console (this part), and one on the server itself (handled automatically by
our setup script in Part 5).

1. On your instance page, under **Primary VNIC**, click the **Subnet** link.
2. Click the **Security List** (usually *Default Security List for …*).
3. Click **Add Ingress Rules** and add **two** rules:

   | Source CIDR | IP Protocol | Destination Port |
   |-------------|-------------|------------------|
   | `0.0.0.0/0` | TCP         | `80`             |
   | `0.0.0.0/0` | TCP         | `443`            |

   (`0.0.0.0/0` just means "allow visitors from anywhere", which is what a
   public website needs.)
4. Click **Add Ingress Rules** to save.

---

## Part 3 — Point your domain at the server

You're using the free domain **`missuniverse.dpdns.org`** from DigitalPlat, so
you manage its DNS from the **DigitalPlat dashboard** — no purchase needed.

1. Sign in to your **DigitalPlat dashboard** and open **DNS management** for
   **`missuniverse.dpdns.org`**.
2. Add a single **A record** pointing at your server:

   | Type | Name / Host                | Value / Points to |
   |------|----------------------------|-------------------|
   | `A`  | `@` *(or `missuniverse`)*  | YOUR_SERVER_IP    |

   - Use **`@`** if the panel is already scoped to `missuniverse.dpdns.org`. If
     instead it asks for a name under `dpdns.org`, type **`missuniverse`**.
   - There is **no `www`** to add — a subdomain like this is used exactly as it
     is.
3. **⚠️ The one setting that quietly breaks the padlock:** if you see a **cloud
   icon** or a **"Proxy" / "Proxied"** toggle next to the record (DigitalPlat
   runs on Cloudflare), set it to **"DNS only" (grey cloud)** — *not* "Proxied"
   (orange cloud). This lets your own server fetch its HTTPS certificate.
   *(If there's no such toggle, there's nothing to change — carry on.)*
4. Save. DNS changes usually take a few minutes (occasionally longer) to spread
   across the internet. You can keep going with the next parts meanwhile.

> ℹ️ Your domain — `missuniverse.dpdns.org` — is exactly what goes into `DOMAIN`
> in Part 5: no `www`, no `https://`, just that.

---

## Part 4 — Connect to your server

You'll use **SSH**, a secure remote terminal. On **Windows 10/11** it's built in.

1. Open **PowerShell** (press Start, type *PowerShell*, hit Enter).
2. Connect, replacing the key path and IP with yours:

   ```bash
   ssh -i C:\Users\YOU\nailstudio-key.key ubuntu@YOUR_SERVER_IP
   ```

   - The username is **`ubuntu`** for the Ubuntu image.
   - The first time, it asks *"Are you sure…?"* — type **`yes`** and press Enter.
   - If it complains the key is *"too open"/permissions*, run this once (adjust
     the path) and try again:

     ```bash
     icacls "C:\Users\YOU\nailstudio-key.key" /inheritance:r /grant:r "%USERNAME%:R"
     ```

3. When you see a prompt like `ubuntu@nailstudio:~$`, you're **in**. 🎉

> Prefer clicking to typing? You can install **PuTTY** instead — but PowerShell
> above needs nothing extra.

---

## Part 5 — Put your site on the server

Now we get your code onto the server and tell it your settings.

### 5a. Get the code onto the server

**Recommended — via GitHub** (easiest to update later). If your project is on
GitHub:

```bash
git clone https://github.com/YOUR_USERNAME/YOUR_REPO.git nailstudio
cd nailstudio
```

> **Not on GitHub yet?** No problem — just ask me and I'll walk you through
> creating a free GitHub repo and pushing this folder (it's about 3 clicks and
> 2 commands). Your secrets are **not** included — the `.env` file is ignored on
> purpose, which is exactly why this is safe.
>
> **No‑GitHub alternative:** install **WinSCP** on your PC, connect with the
> same key and IP, and drag this whole project folder onto the server. Then
> `cd` into it.

### 5b. Prepare the server (install Docker + open firewall)

```bash
bash deploy/oracle-setup.sh
```

When it finishes, run this once so you don't need `sudo` for Docker:

```bash
newgrp docker
```

### 5c. Create your live settings file

Copy the example and open it in the simple `nano` editor:

```bash
cp .env.example .env
nano .env
```

Change these values (arrow keys to move, just type to edit):

| Setting          | Set it to…                                             |
|------------------|--------------------------------------------------------|
| `ENV`            | `production`                                           |
| `DOMAIN`         | `missuniverse.dpdns.org` (no `https://`)               |
| `BASE_URL`       | `https://missuniverse.dpdns.org` (same, **with** https) |
| `SECRET_KEY`     | a long random string — see the tip below               |
| `ADMIN_EMAIL`    | the email you'll log in with                           |
| `ADMIN_PASSWORD` | a strong password you'll remember                      |

Your **WhatsApp number, contact details and social links** are already filled in
from before — leave them as they are (or tweak if needed).

> 🔑 **Need a SECRET_KEY?** Run this in the server terminal and paste the result:
>
> ```bash
> python3 -c "import secrets; print(secrets.token_urlsafe(48))"
> ```

**Save and exit nano:** press **Ctrl + O**, then **Enter** (saves), then
**Ctrl + X** (exits).

---

## Part 6 — Launch! 🚀

One command builds and starts everything:

```bash
docker compose -f docker-compose.prod.yml up -d --build
```

- The first build takes about **2–5 minutes** (it's downloading and assembling
  things). Later restarts are seconds.
- Caddy then automatically requests your **free HTTPS certificate**. This needs
  your DNS (Part 3) to be pointing correctly and can take up to a minute or two.

Check that both parts are running:

```bash
docker compose -f docker-compose.prod.yml ps
```

You want to see **`web`** and **`caddy`** both `running`/`Up`.

---

## Part 7 — You're live 🎉

1. Open **`https://missuniverse.dpdns.org`** in your browser. You should see your
   site with a **padlock 🔒** next to the address.
2. Go to **`https://missuniverse.dpdns.org/admin`** and log in with the
   `ADMIN_EMAIL` / `ADMIN_PASSWORD` you set.
3. Start adding your real designs and categories from the admin panel.

> Your live catalogue **starts empty** (no demo designs in production) — that's
> intentional, so customers only ever see your real work. Add designs via the
> admin panel.

---

## Everyday tasks

Run these on the server, from inside the project folder (`cd nailstudio`).

### See what's happening (logs)

```bash
docker compose -f docker-compose.prod.yml logs -f
```

(Press **Ctrl + C** to stop watching — this does *not* stop the site.)

### Update the site after you change the code

If you used GitHub:

```bash
git pull
docker compose -f docker-compose.prod.yml up -d --build
```

### Change the admin password (or email)

Edit `.env` (`nano .env`), then apply it:

```bash
docker compose -f docker-compose.prod.yml exec web python manage.py reset-admin
```

### Restart or stop the site

```bash
docker compose -f docker-compose.prod.yml restart      # restart
docker compose -f docker-compose.prod.yml down         # stop (data is kept)
```

### Back up your data (do this regularly!)

Your designs (database) and uploaded photos live in Docker *volumes*. First see
their exact names:

```bash
docker volume ls
```

Then back them up into files in your current folder (swap in the names you saw —
they usually start with `nailstudio_`):

```bash
docker run --rm -v nailstudio_data:/d -v "$PWD":/b alpine tar czf /b/backup-database.tgz -C /d .
docker run --rm -v nailstudio_uploads:/d -v "$PWD":/b alpine tar czf /b/backup-photos.tgz -C /d .
```

Copy those `.tgz` files to your PC with **WinSCP** for safekeeping.

---

## Troubleshooting

**The site won't load at all.**
- Give DNS more time (Part 3) — check progress at <https://dnschecker.org>.
- Make sure you opened ports 80 **and** 443 in Oracle's Security List (Part 2).
- On the server, confirm both containers are up:
  `docker compose -f docker-compose.prod.yml ps`.

**No padlock / "certificate" error / HTTPS fails.**
- Caddy needs port **80** reachable from the internet and your **DNS A record**
  pointing at the server to get the certificate. Re-check Parts 2 and 3.
- Look at Caddy's messages:
  `docker compose -f docker-compose.prod.yml logs caddy`.
- Also make sure `DOMAIN` in `.env` matches the address you're visiting.
- **DigitalPlat / Cloudflare:** if the DNS record is **Proxied** (orange cloud),
  your server can't fetch its own certificate — switch it to **DNS only**
  (Part 3, step 3). If the panel won't let you turn proxying off at all, tell me
  and I'll give you the alternative Cloudflare-proxy setup instead.

**"Out of host capacity" when creating the ARM instance.**
- Oracle's free ARM machines are popular. Try again later, try a different
  Availability Domain, or use the **VM.Standard.E2.1.Micro** shape instead
  (Part 1, step 5).

**`docker: permission denied` / it asks for sudo.**
- Run `newgrp docker` (or log out of SSH and reconnect), then retry.

**Will Oracle delete my free server?**
- Always Free *idle* compute instances can be reclaimed. A real website that
  gets visitors isn't idle, so this normally won't affect you. Keeping regular
  **backups** (above) means you're covered regardless.

---

## Safety notes (already handled for you)

- Setting `ENV=production` makes the app **require HTTPS** and use **secure
  cookies** — that's why we put Caddy in front.
- Your secrets live **only** in the server's `.env` file. It is never committed
  to GitHub (it's in `.gitignore`), so putting your code on a public repo is
  safe.
- Please make sure you changed `ADMIN_PASSWORD` from the default in Part 5.

---

*That's everything. Once it's live, you manage the whole catalogue from
`/admin` in your browser — no need to touch the server again except for the
occasional update or backup.*

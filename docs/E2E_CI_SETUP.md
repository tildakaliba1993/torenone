# Turning on the nightly E2E test (simple guide)

This sets up the automated end-to-end test that runs every night. It needs its **own
throwaway Supabase project** (so it never touches your real data).

**You only do the clicking in the Supabase website (Part A).** Then you paste 6 things to
Claude, and **Claude does the rest** (database setup, GitHub secrets, first run). That's it.

---

## Part A — what YOU click (about 10 minutes, all in the Supabase website)

### Step 1 — Make a new project
1. Go to **https://supabase.com/dashboard** and sign in.
2. Click the green **"New project"** button.
3. Name it **`torenone-e2e`**.
4. Where it says **Database Password**, click **"Generate a password"**, then **copy that
   password and paste it somewhere safe** (a note). You'll give it to Claude later. ⚠️ You
   can't see it again after this.
5. Pick the same region as your main project, then click **"Create new project"**.
6. Wait ~2 minutes for it to finish setting up (you'll see a progress spinner).

### Step 2 — Turn off email confirmation
1. In the left sidebar click **Authentication**.
2. Click **Sign In / Providers** (or just **Providers**).
3. Click **Email** in the list.
4. Find the **"Confirm email"** switch and turn it **OFF**.
5. Click **Save**.

*(This lets the test log in without checking an inbox.)*

### Step 3 — Create the test login user
1. Still under **Authentication**, click **Users**.
2. Click **Add user** → **Create new user**.
3. Email: **`e2e@torenone.test`**
4. Password: make up a password and **save it in your note** (you'll give it to Claude).
5. Tick the **"Auto Confirm User"** box.
6. Click **Create user**.

### Step 4 — Copy 4 values from Settings
1. Click the **gear / Project Settings** at the bottom of the left sidebar.
2. Click **API**. Copy these three (paste each into your note):
   - **Project URL** (looks like `https://abcd1234.supabase.co`)
   - **anon** key (the "public" one)
   - **service_role** key (the "secret" one — keep it private)
3. Click **Database** (still in Settings). Find **Connection string**, choose the **URI**
   tab, and copy it. It looks like
   `postgresql://postgres:[YOUR-PASSWORD]@db.abcd1234.supabase.co:5432/postgres`.

That's all the clicking. ✅

---

## Part B — paste these 6 things to Claude, and you're done

Send Claude a message with:

1. **Project URL** (from Step 4)
2. **anon key** (from Step 4)
3. **service_role key** (from Step 4)
4. **Connection string** (from Step 4) — with `[YOUR-PASSWORD]` replaced by the database
   password from Step 1
5. **Test user email** → `e2e@torenone.test`
6. **Test user password** (from Step 3)

> These belong to a *throwaway test project* with no real data, so they're low-stakes — but
> if you'd rather not paste the two secret ones (service_role key, connection string) into
> chat, tell Claude and it'll give you a couple of copy-paste commands to set them yourself.

**Claude then automatically:**
- builds the test database (runs the 4 migrations) and checks the test user can sign in,
- saves all 7 values as GitHub secrets and flips the `RUN_E2E` switch on,
- starts the first nightly-style run and watches it go green,
- reports back with the result.

After that it runs **every night at 02:00 UTC** on its own. To pause it later, just ask
Claude to "turn off the nightly E2E" (it flips one switch).

-- TorenOne auth → profile/firm bootstrap (Phase 5, Task 5.2) — Design §A.7.
--
-- When Supabase Auth creates a new user (email sign-up), we must create the
-- matching `profiles` row and link it to a `firm` (the tenant). Two cases:
--
--   * Invited to an existing firm — the sign-up metadata carries `firm_id`; the
--     new user joins that firm as an 'engineer'.
--   * First user of a new firm — no `firm_id` in metadata; we create a new firm
--     (named from `firm_name`, else derived from the email) and the user 'owns' it.
--
-- The trigger runs SECURITY DEFINER (it writes rows the signing-up user cannot yet
-- write — they have no profile, so the Task 5.4 RLS policies would otherwise block
-- the insert). search_path is pinned empty and every object is schema-qualified, so
-- the definer function cannot be hijacked via a mutable search_path.

create or replace function public.handle_new_user()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
declare
    v_firm_id   uuid;
    v_firm_name text;
    v_role      text;
begin
    -- Invited to an existing firm? Metadata carries a firm_id.
    v_firm_id := nullif(new.raw_user_meta_data ->> 'firm_id', '')::uuid;

    if v_firm_id is null then
        -- First user of a new firm: create the firm; this user owns it.
        v_firm_name := coalesce(
            nullif(new.raw_user_meta_data ->> 'firm_name', ''),
            'Firm of ' || coalesce(new.email, new.id::text)
        );
        insert into public.firms (name)
        values (v_firm_name)
        returning id into v_firm_id;
        v_role := 'owner';
    else
        v_role := 'engineer';
    end if;

    insert into public.profiles (id, firm_id, name, role)
    values (
        new.id,
        v_firm_id,
        nullif(new.raw_user_meta_data ->> 'full_name', ''),
        v_role
    );

    return new;
end;
$$;

-- Fire once per newly-created auth user.
create trigger on_auth_user_created
    after insert on auth.users
    for each row execute function public.handle_new_user();
